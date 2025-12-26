"""
Slack Service - Socket Mode integration for Slack.

Provides:
- SlackBot class with Socket Mode
- Direct message handling
- User linking to VAM accounts
- Proactive messaging capabilities
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from threading import Thread

# Logging
try:
    from app.core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# Slack Configuration
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")  # xoxb-...
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")  # xapp-...
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")


class SlackService:
    """
    Slack service using Socket Mode for real-time messaging.
    No webhook/firewall setup required.
    """
    
    def __init__(self):
        self.bot_token = SLACK_BOT_TOKEN
        self.app_token = SLACK_APP_TOKEN
        self._app = None
        self._handler = None
        self._running = False
        self._message_handlers: List[Callable] = []
    
    @property
    def is_configured(self) -> bool:
        """Check if Slack is properly configured."""
        return bool(self.bot_token and self.app_token)
    
    def _init_bolt(self):
        """Initialize Slack Bolt app lazily."""
        if self._app is not None:
            return True
        
        if not self.is_configured:
            logger.warning("Slack not configured. Set SLACK_BOT_TOKEN and SLACK_APP_TOKEN.")
            return False
        
        try:
            from slack_bolt import App
            from slack_bolt.adapter.socket_mode import SocketModeHandler
            
            self._app = App(token=self.bot_token)
            self._handler = SocketModeHandler(self._app, self.app_token)
            
            # Register event handlers
            @self._app.event("message")
            def handle_message(event, say, client):
                self._process_message(event, say, client)
            
            @self._app.event("app_mention")
            def handle_mention(event, say):
                say(f"Hi <@{event['user']}>! You can send me a direct message to interact with VAM.")
            
            logger.info("Slack Bolt app initialized successfully")
            return True
            
        except ImportError:
            logger.error("slack-bolt not installed. Run: pip install slack-bolt")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Slack app: {e}")
            return False
    
    def _process_message(self, event: Dict, say: Callable, client):
        """Process incoming Slack messages."""
        # Ignore bot messages
        if event.get("bot_id") or event.get("subtype") == "bot_message":
            return
        
        channel = event.get("channel", "")
        user_id = event.get("user", "")
        text = event.get("text", "")
        
        # Only process DMs (channel type starts with 'D')
        if not channel.startswith("D"):
            return
        
        logger.info(f"Received DM from {user_id}: {text[:50]}...")
        
        # Process with registered handlers
        for handler in self._message_handlers:
            try:
                response = handler(user_id, text, event)
                if response:
                    say(response)
                    return
            except Exception as e:
                logger.error(f"Message handler error: {e}")
        
        # Default response if no handler matched
        say("I received your message! I'm VAM, your Virtual AI Manager. How can I help you today?")
    
    def register_message_handler(self, handler: Callable):
        """
        Register a message handler function.
        
        Handler signature: handler(slack_user_id: str, text: str, event: dict) -> Optional[str]
        Return a string to respond, or None to let other handlers process.
        """
        self._message_handlers.append(handler)
    
    def start(self, blocking: bool = False):
        """
        Start the Slack bot.
        
        Args:
            blocking: If True, blocks the current thread. If False, runs in background.
        """
        if not self._init_bolt():
            return False
        
        if self._running:
            logger.warning("Slack bot already running")
            return True
        
        try:
            if blocking:
                logger.info("Starting Slack bot (blocking mode)...")
                self._running = True
                self._handler.start()
            else:
                logger.info("Starting Slack bot (background mode)...")
                self._running = True
                thread = Thread(target=self._handler.start, daemon=True)
                thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start Slack bot: {e}")
            self._running = False
            return False
    
    def stop(self):
        """Stop the Slack bot."""
        if self._handler and self._running:
            try:
                self._handler.close()
                self._running = False
                logger.info("Slack bot stopped")
            except Exception as e:
                logger.error(f"Error stopping Slack bot: {e}")
    
    async def send_dm(
        self,
        slack_user_id: str,
        message: str,
        blocks: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Send a direct message to a Slack user.
        
        Args:
            slack_user_id: Slack user ID (e.g., U12345)
            message: Text message to send
            blocks: Optional Slack blocks for rich formatting
        
        Returns:
            Message send result
        """
        if not self.is_configured:
            return {"success": False, "error": "Slack not configured"}
        
        try:
            from slack_sdk import WebClient
            from slack_sdk.errors import SlackApiError
            
            client = WebClient(token=self.bot_token)
            
            # Open DM channel
            dm_response = client.conversations_open(users=[slack_user_id])
            channel_id = dm_response["channel"]["id"]
            
            # Send message
            params = {
                "channel": channel_id,
                "text": message
            }
            if blocks:
                params["blocks"] = blocks
            
            result = client.chat_postMessage(**params)
            
            logger.info(f"Sent DM to {slack_user_id}")
            return {
                "success": True,
                "channel": channel_id,
                "ts": result["ts"],
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Failed to send DM to {slack_user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_user_info(self, slack_user_id: str) -> Dict[str, Any]:
        """
        Get Slack user information.
        
        Args:
            slack_user_id: Slack user ID
        
        Returns:
            User profile info
        """
        if not self.is_configured:
            return {"success": False, "error": "Slack not configured"}
        
        try:
            from slack_sdk import WebClient
            
            client = WebClient(token=self.bot_token)
            result = client.users_info(user=slack_user_id)
            
            user = result["user"]
            profile = user.get("profile", {})
            
            return {
                "success": True,
                "slack_id": slack_user_id,
                "name": user.get("real_name", user.get("name")),
                "email": profile.get("email"),
                "display_name": profile.get("display_name"),
                "avatar_url": profile.get("image_192"),
                "timezone": user.get("tz"),
                "timezone_offset": user.get("tz_offset")
            }
            
        except Exception as e:
            logger.error(f"Failed to get user info for {slack_user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    async def send_standup_prompt(
        self,
        slack_user_id: str,
        github_issues: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Send morning standup prompt to a user.
        
        Args:
            slack_user_id: Slack user ID
            github_issues: List of assigned GitHub issues from Phase 1
        
        Returns:
            Message result
        """
        # Build issue list
        issue_lines = []
        for i, issue in enumerate(github_issues[:5], 1):  # Max 5 issues
            issue_lines.append(f"{i}. {issue.get('title', 'Untitled')}")
        
        issues_text = "\n".join(issue_lines) if issue_lines else "No issues assigned"
        
        message = f"""☀️ Good morning! Here's your standup check-in.

*GitHub Issues assigned to you:*
{issues_text}

What's your focus for today? Just reply with what you're working on, and I'll block time on your calendar."""
        
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "☀️ *Good morning!* Here's your standup check-in."
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*GitHub Issues assigned to you:*\n{issues_text}"
                }
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "What's your focus for today? Just reply with what you're working on, and I'll block time on your calendar. 📅"
                }
            }
        ]
        
        return await self.send_dm(slack_user_id, message, blocks)


# Singleton instance
_slack_service: Optional[SlackService] = None


def get_slack_service() -> SlackService:
    """Get the singleton Slack service instance."""
    global _slack_service
    if _slack_service is None:
        _slack_service = SlackService()
    return _slack_service


async def link_slack_user(
    vam_user_id: str,
    slack_user_id: str,
    db_session
) -> Dict[str, Any]:
    """
    Link a Slack user to a VAM user account.
    
    Args:
        vam_user_id: VAM user ID
        slack_user_id: Slack user ID
        db_session: Database session
    
    Returns:
        Link result
    """
    try:
        from app.models import UserIntegration
    except ImportError:
        from backend.app.models import UserIntegration
    
    import uuid
    
    # Get Slack user info
    service = get_slack_service()
    user_info = await service.get_user_info(slack_user_id)
    
    if not user_info.get("success"):
        return {"success": False, "error": user_info.get("error")}
    
    # Check for existing integration
    existing = db_session.query(UserIntegration).filter(
        UserIntegration.user_id == vam_user_id,
        UserIntegration.provider == "slack"
    ).first()
    
    now = datetime.utcnow()
    
    if existing:
        existing.provider_user_id = slack_user_id
        existing.provider_email = user_info.get("email")
        existing.provider_metadata = json.dumps(user_info)
        existing.is_active = True
        existing.updated_at = now
    else:
        integration = UserIntegration(
            id=str(uuid.uuid4()),
            user_id=vam_user_id,
            provider="slack",
            provider_user_id=slack_user_id,
            provider_email=user_info.get("email"),
            provider_metadata=json.dumps(user_info),
            is_active=True,
            created_at=now,
            updated_at=now
        )
        db_session.add(integration)
    
    db_session.commit()
    
    logger.info(f"Linked Slack user {slack_user_id} to VAM user {vam_user_id}")
    return {
        "success": True,
        "slack_user_id": slack_user_id,
        "slack_email": user_info.get("email"),
        "slack_name": user_info.get("name")
    }


async def get_slack_user_id(vam_user_id: str, db_session) -> Optional[str]:
    """Get the Slack user ID for a VAM user."""
    try:
        from app.models import UserIntegration
    except ImportError:
        from backend.app.models import UserIntegration
    
    integration = db_session.query(UserIntegration).filter(
        UserIntegration.user_id == vam_user_id,
        UserIntegration.provider == "slack",
        UserIntegration.is_active == True
    ).first()
    
    return integration.provider_user_id if integration else None
