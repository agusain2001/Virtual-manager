"""
Standup Handler - Manages proactive morning standup conversations.

The standup flow:
1. Scheduler triggers at 09:00 local time
2. Fetch user's GitHub issues (from Phase 1)
3. Send Slack DM asking for daily focus
4. Process response and create calendar block
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

# Logging
try:
    from app.core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# Track ongoing standup conversations (user_id -> conversation state)
_standup_state: Dict[str, Dict[str, Any]] = {}


async def initiate_standup(user_id: str, db: Session) -> Dict[str, Any]:
    """
    Initiate a morning standup conversation with a user.
    
    Args:
        user_id: VAM user ID
        db: Database session
    
    Returns:
        Result of initiating the standup
    """
    try:
        from app.services.slack_service import get_slack_service, get_slack_user_id
        from app.services.github_service import GitHubService
        from app.models import User
    except ImportError:
        from backend.app.services.slack_service import get_slack_service, get_slack_user_id
        from backend.app.services.github_service import GitHubService
        from backend.app.models import User
    
    # Get the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"success": False, "error": "User not found"}
    
    # Get Slack user ID
    slack_user_id = await get_slack_user_id(user_id, db)
    if not slack_user_id:
        return {"success": False, "error": "User has no Slack linked", "user_id": user_id}
    
    # Fetch GitHub issues assigned to user
    github_issues = []
    if user.github_access_token and user.default_github_repo:
        try:
            github_service = GitHubService(access_token=user.github_access_token)
            # Get open issues assigned to the user
            issues = await github_service.get_user_issues(user.github_username)
            github_issues = issues[:5]  # Limit to 5
        except Exception as e:
            logger.warning(f"Could not fetch GitHub issues for {user_id}: {e}")
    
    # Send standup prompt
    service = get_slack_service()
    result = await service.send_standup_prompt(slack_user_id, github_issues)
    
    if result.get("success"):
        # Track conversation state
        _standup_state[user_id] = {
            "started_at": datetime.utcnow().isoformat(),
            "slack_user_id": slack_user_id,
            "github_issues": github_issues,
            "awaiting_response": True
        }
        logger.info(f"Initiated standup for user {user_id}")
    
    return result


async def process_standup_response(
    user_id: str,
    response_text: str,
    db: Session
) -> Dict[str, Any]:
    """
    Process a user's standup response and create calendar block.
    
    Args:
        user_id: VAM user ID
        response_text: User's response about their focus
        db: Database session
    
    Returns:
        Result including any calendar actions taken
    """
    try:
        from app.mcp.calendar import schedule_focus_block, find_free_slot
        from app.services.slack_service import get_slack_service, get_slack_user_id
    except ImportError:
        from backend.app.mcp.calendar import schedule_focus_block, find_free_slot
        from backend.app.services.slack_service import get_slack_service, get_slack_user_id
    
    # Parse the focus from response
    focus_task = extract_focus_from_response(response_text)
    
    if not focus_task:
        return {
            "success": False,
            "error": "Could not understand your focus. Please describe what you're working on."
        }
    
    # Find a free slot for today
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    free_slot = await find_free_slot(
        user_id=user_id,
        date=today,
        duration_minutes=120,  # 2 hour focus block
        db=db
    )
    
    if not free_slot:
        # Try to find any slot
        free_slot = await find_free_slot(
            user_id=user_id,
            date=today,
            duration_minutes=60,  # Try 1 hour
            db=db
        )
    
    result = {
        "success": True,
        "focus_task": focus_task,
        "calendar_blocked": False
    }
    
    if free_slot:
        # Schedule focus block
        start_time = datetime.fromisoformat(free_slot["start"])
        duration = min(free_slot.get("duration_minutes", 120), 120)  # Max 2 hours
        
        block_result = await schedule_focus_block(
            user_id=user_id,
            task_title=focus_task,
            start_time=start_time,
            duration_minutes=duration,
            db=db
        )
        
        if block_result.get("success"):
            result["calendar_blocked"] = True
            result["block_start"] = start_time.strftime("%I:%M %p")
            result["block_end"] = (start_time + timedelta(minutes=duration)).strftime("%I:%M %p")
            result["event_id"] = block_result.get("event_id")
    else:
        result["calendar_note"] = "No free slots found today"
    
    # Send confirmation via Slack
    slack_user_id = await get_slack_user_id(user_id, db)
    if slack_user_id:
        service = get_slack_service()
        
        if result.get("calendar_blocked"):
            message = f"✅ Got it! I've blocked *{result['block_start']} - {result['block_end']}* on your calendar for:\n\n🎯 *{focus_task}*\n\nHave a productive day!"
        else:
            message = f"✅ Got it! Your focus today is:\n\n🎯 *{focus_task}*\n\n(Couldn't find a free slot to block on your calendar)"
        
        await service.send_dm(slack_user_id, message)
    
    # Clear conversation state
    if user_id in _standup_state:
        del _standup_state[user_id]
    
    logger.info(f"Processed standup for {user_id}: focus={focus_task}, blocked={result.get('calendar_blocked')}")
    
    return result


def extract_focus_from_response(text: str) -> Optional[str]:
    """
    Extract the focus task from user's natural language response.
    
    Examples:
    - "I'm working on the API" -> "API"
    - "Today I'll focus on fixing the login bug" -> "Fixing the login bug"
    - "Backend refactoring" -> "Backend refactoring"
    """
    text = text.strip()
    
    if not text:
        return None
    
    # Remove common prefixes
    prefixes = [
        r"^(i'm|im|i am) working on\s+",
        r"^(i'll|i will) focus on\s+",
        r"^(i'll|i will) work on\s+",
        r"^(today|today's focus is|my focus is|focusing on)\s+",
        r"^working on\s+",
        r"^focus(ing)? on\s+",
    ]
    
    for prefix in prefixes:
        text = re.sub(prefix, "", text, flags=re.IGNORECASE)
    
    # Remove trailing punctuation
    text = text.rstrip(".")
    
    # Capitalize first letter
    if text:
        text = text[0].upper() + text[1:]
    
    return text if text else None


def register_standup_message_handler():
    """
    Register the standup response handler with the Slack service.
    Called when the app starts.
    """
    try:
        from app.services.slack_service import get_slack_service
        from app.core.database import SessionLocal
    except ImportError:
        from backend.app.services.slack_service import get_slack_service
        from backend.app.core.database import SessionLocal
    
    service = get_slack_service()
    
    def handle_standup_response(slack_user_id: str, text: str, event: Dict) -> Optional[str]:
        """Handle incoming messages that might be standup responses."""
        import asyncio
        
        # Find user by Slack ID
        db = SessionLocal()
        try:
            from app.models import UserIntegration
        except ImportError:
            from backend.app.models import UserIntegration
        
        try:
            integration = db.query(UserIntegration).filter(
                UserIntegration.provider_user_id == slack_user_id,
                UserIntegration.provider == "slack",
                UserIntegration.is_active == True
            ).first()
            
            if not integration:
                return None  # Let other handlers process
            
            user_id = integration.user_id
            
            # Check if user has an active standup
            if user_id in _standup_state and _standup_state[user_id].get("awaiting_response"):
                # Process the standup response
                loop = asyncio.new_event_loop()
                try:
                    result = loop.run_until_complete(
                        process_standup_response(user_id, text, db)
                    )
                    # Response is sent in process_standup_response
                    return None  # Already handled
                finally:
                    loop.close()
            
            return None  # Let other handlers process
            
        finally:
            db.close()
    
    service.register_message_handler(handle_standup_response)
    logger.info("Registered standup message handler")


async def trigger_standup_for_all_users(db: Session) -> Dict[str, Any]:
    """
    Trigger standup for all users with Slack linked.
    Called by the scheduler.
    """
    try:
        from app.models import UserIntegration
    except ImportError:
        from backend.app.models import UserIntegration
    
    # Get all users with active Slack integration
    slack_users = db.query(UserIntegration).filter(
        UserIntegration.provider == "slack",
        UserIntegration.is_active == True,
        UserIntegration.provider_user_id.isnot(None)
    ).all()
    
    results = {
        "total": len(slack_users),
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    for integration in slack_users:
        try:
            result = await initiate_standup(integration.user_id, db)
            if result.get("success"):
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "user_id": integration.user_id,
                    "error": result.get("error")
                })
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "user_id": integration.user_id,
                "error": str(e)
            })
    
    logger.info(f"Standup triggered: {results['success']}/{results['total']} successful")
    return results
