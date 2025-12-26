"""
Google OAuth Router - Handles Google Calendar integration.

Provides OAuth flow for connecting Google Calendar:
- /auth/google/connect - Redirect to Google consent
- /auth/google/callback - Handle OAuth callback
- /auth/google/status - Check connection status
- /auth/google/disconnect - Remove integration
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import httpx

# Try different import paths
try:
    from backend.app.core.database import get_db
    from backend.app.models import User, UserIntegration
except ImportError:
    from app.core.database import get_db
    from app.models import User, UserIntegration

router = APIRouter(prefix="/auth/google", tags=["Google OAuth"])

# Google OAuth Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# Scopes for Google Calendar
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]


def get_current_user_id(request: Request) -> Optional[str]:
    """Extract user ID from JWT cookie (shared with GitHub auth)."""
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


@router.get("/connect")
async def connect_google(request: Request, db: Session = Depends(get_db)):
    """
    Redirect user to Google OAuth consent screen.
    Requires user to be logged in via GitHub first.
    """
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Please sign in with GitHub first before connecting Google Calendar"
        )
    
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID in environment."
        )
    
    # Build OAuth URL
    state = f"{user_id}"  # Pass user_id in state for callback
    
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",  # Get refresh token
        "prompt": "consent",  # Force consent to get refresh token
        "state": state,
    }
    
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback.
    Exchange code for tokens and save to user_integrations.
    """
    if error:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?error=google_auth_failed&message={error}"
        )
    
    if not code or not state:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?error=missing_params"
        )
    
    user_id = state
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?error=user_not_found"
        )
    
    # Exchange code for tokens
    try:
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": GOOGLE_REDIRECT_URI,
                }
            )
            
            if token_response.status_code != 200:
                return RedirectResponse(
                    url=f"{FRONTEND_URL}/settings?error=token_exchange_failed"
                )
            
            tokens = token_response.json()
            access_token = tokens.get("access_token")
            refresh_token = tokens.get("refresh_token")
            expires_in = tokens.get("expires_in", 3600)
            
            # Get user info from Google
            user_info_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            google_user = user_info_response.json() if user_info_response.status_code == 200 else {}
            
    except Exception as e:
        return RedirectResponse(
            url=f"{FRONTEND_URL}/settings?error=google_api_error&message={str(e)}"
        )
    
    # Check for existing integration
    existing = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "google"
    ).first()
    
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=expires_in)
    
    if existing:
        # Update existing integration
        existing.access_token = access_token
        if refresh_token:  # Only update if new refresh token provided
            existing.refresh_token = refresh_token
        existing.token_expires_at = expires_at
        existing.scopes = json.dumps(GOOGLE_SCOPES)
        existing.provider_user_id = google_user.get("id")
        existing.provider_email = google_user.get("email")
        existing.provider_metadata = json.dumps(google_user)
        existing.is_active = True
        existing.sync_error = None
        existing.updated_at = now
    else:
        # Create new integration
        integration = UserIntegration(
            id=str(uuid.uuid4()),
            user_id=user_id,
            provider="google",
            access_token=access_token,
            refresh_token=refresh_token,
            token_expires_at=expires_at,
            scopes=json.dumps(GOOGLE_SCOPES),
            provider_user_id=google_user.get("id"),
            provider_email=google_user.get("email"),
            provider_metadata=json.dumps(google_user),
            is_active=True,
            created_at=now,
            updated_at=now
        )
        db.add(integration)
    
    db.commit()
    
    return RedirectResponse(
        url=f"{FRONTEND_URL}/settings?success=google_connected"
    )


@router.get("/status")
async def google_status(request: Request, db: Session = Depends(get_db)):
    """Check if Google Calendar is connected for the current user."""
    user_id = get_current_user_id(request)
    if not user_id:
        return {"connected": False, "reason": "not_authenticated"}
    
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "google",
        UserIntegration.is_active == True
    ).first()
    
    if not integration:
        return {"connected": False, "reason": "not_connected"}
    
    # Check if token is expired
    if integration.token_expires_at and integration.token_expires_at < datetime.utcnow():
        return {
            "connected": True,
            "expired": True,
            "email": integration.provider_email,
            "last_sync": integration.last_sync_at.isoformat() if integration.last_sync_at else None
        }
    
    return {
        "connected": True,
        "expired": False,
        "email": integration.provider_email,
        "scopes": json.loads(integration.scopes) if integration.scopes else [],
        "last_sync": integration.last_sync_at.isoformat() if integration.last_sync_at else None
    }


@router.post("/disconnect")
async def disconnect_google(request: Request, db: Session = Depends(get_db)):
    """Disconnect Google Calendar integration."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "google"
    ).first()
    
    if integration:
        integration.is_active = False
        integration.access_token = None
        integration.refresh_token = None
        integration.updated_at = datetime.utcnow()
        db.commit()
    
    return {"status": "disconnected", "provider": "google"}


@router.get("/refresh")
async def refresh_google_token(request: Request, db: Session = Depends(get_db)):
    """Refresh the Google access token using the refresh token."""
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    integration = db.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "google",
        UserIntegration.is_active == True
    ).first()
    
    if not integration or not integration.refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "refresh_token": integration.refresh_token,
                    "grant_type": "refresh_token",
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Token refresh failed")
            
            tokens = response.json()
            integration.access_token = tokens.get("access_token")
            integration.token_expires_at = datetime.utcnow() + timedelta(
                seconds=tokens.get("expires_in", 3600)
            )
            integration.updated_at = datetime.utcnow()
            db.commit()
            
            return {"status": "refreshed", "expires_at": integration.token_expires_at.isoformat()}
            
    except HTTPException:
        raise
    except Exception as e:
        integration.sync_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Refresh error: {str(e)}")
