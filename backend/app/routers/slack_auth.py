"""
Slack Auth Router - Handles Slack user linking and management.

Provides endpoints for:
- /auth/slack/link - Link Slack user to VAM account
- /auth/slack/status - Check Slack connection status
- /auth/slack/unlink - Remove Slack integration
"""

import os
import json
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

# Try different import paths
try:
    from backend.app.core.database import get_db
    from backend.app.models import User, UserIntegration
    from backend.app.services.slack_service import link_slack_user, get_slack_service
except ImportError:
    from app.core.database import get_db
    from app.models import User, UserIntegration
    from app.services.slack_service import link_slack_user, get_slack_service

router = APIRouter(prefix="/auth/slack", tags=["Slack Integration"])


def get_current_user_id(request: Request) -> Optional[str]:
    """Extract user ID from JWT cookie."""
    import jwt
    
    token = request.cookies.get("vam_session")
    if not token:
        return None
    
    try:
        jwt_secret = os.getenv("JWT_SECRET", "vam-secret-key-change-in-production")
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        return payload.get("user_id")
    except Exception:
        return None


class SlackLinkRequest(BaseModel):
    """Request body for linking Slack user."""
    slack_user_id: str


class SlackLinkByEmailRequest(BaseModel):
    """Request body for linking by email lookup."""
    slack_email: str


@router.post("/link")
async def link_slack(
    request: Request,
    body: SlackLinkRequest,
    db: Session = Depends(get_db)
):
    """
    Link a Slack user ID to the current VAM user.
    
    The Slack user ID can be found by:
    1. User sends "/vam link" command in Slack
    2. Bot responds with their Slack user ID
    3. User enters ID here or bot auto-links via callback
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Link the Slack user
    result = await link_slack_user(
        vam_user_id=user_id,
        slack_user_id=body.slack_user_id,
        db_session=db
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return result


@router.get("/status")
async def slack_status(request: Request, db: Session = Depends(get_db)):
    """Check if Slack is connected for the current user."""
    user_id = get_current_user_id(request)
    if not user_id:
        return {"connected": False, "reason": "not_authenticated"}
    
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "slack",
        UserIntegration.is_active == True
    ).first()
    
    if not integration:
        return {"connected": False, "reason": "not_linked"}
    
    # Parse metadata
    metadata = {}
    if integration.provider_metadata:
        try:
            metadata = json.loads(integration.provider_metadata)
        except:
            pass
    
    return {
        "connected": True,
        "slack_user_id": integration.provider_user_id,
        "slack_email": integration.provider_email,
        "slack_name": metadata.get("name"),
        "linked_at": integration.created_at.isoformat() if integration.created_at else None
    }


@router.post("/unlink")
async def unlink_slack(request: Request, db: Session = Depends(get_db)):
    """Remove Slack integration for the current user."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "slack"
    ).first()
    
    if integration:
        integration.is_active = False
        integration.provider_user_id = None
        integration.updated_at = datetime.utcnow()
        db.commit()
    
    return {"status": "unlinked", "provider": "slack"}


@router.get("/bot-status")
async def bot_status():
    """Check if the Slack bot is configured and running."""
    service = get_slack_service()
    
    return {
        "configured": service.is_configured,
        "running": service._running,
        "instructions": (
            "To configure Slack:\n"
            "1. Create a Slack app at https://api.slack.com/apps\n"
            "2. Enable Socket Mode\n"
            "3. Add scopes: chat:write, im:history, users:read\n"
            "4. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN in .env"
        ) if not service.is_configured else None
    }


@router.post("/test-dm")
async def test_dm(
    request: Request,
    db: Session = Depends(get_db)
):
    """Send a test DM to the linked Slack user."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "slack",
        UserIntegration.is_active == True
    ).first()
    
    if not integration or not integration.provider_user_id:
        raise HTTPException(status_code=400, detail="Slack not linked")
    
    service = get_slack_service()
    result = await service.send_dm(
        slack_user_id=integration.provider_user_id,
        message="👋 Hello from VAM! Your Slack integration is working correctly."
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    
    return {"status": "sent", "channel": result.get("channel")}
