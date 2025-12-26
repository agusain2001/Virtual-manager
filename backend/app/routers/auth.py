"""
Authentication Router - GitHub OAuth and Session Management.

Endpoints:
- GET /auth/github - Redirect to GitHub OAuth
- GET /auth/callback/github - Handle OAuth callback
- GET /auth/me - Get current user info
- POST /auth/logout - Clear session
- GET /auth/repos - Get user's GitHub repos
"""

import os
import uuid
import secrets
from typing import Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Response, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import jwt

from backend.app.core.database import get_db
from backend.app.models import User, UserRole
from backend.app.services.github_service import github_service

router = APIRouter(prefix="/auth", tags=["Authentication"])

# JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "vam-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24 * 7  # 1 week

# Frontend URL for redirects
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


class UserResponse(BaseModel):
    """User profile response."""
    id: str
    email: str
    name: str
    role: str
    github_username: Optional[str] = None
    github_avatar_url: Optional[str] = None
    default_github_repo: Optional[str] = None
    is_github_connected: bool = False
    
    class Config:
        from_attributes = True


class RepoResponse(BaseModel):
    """GitHub repository response."""
    id: int
    full_name: str
    name: str
    private: bool
    description: Optional[str] = None
    html_url: str


class SetDefaultRepoRequest(BaseModel):
    """Request to set default repo."""
    repo: str  # "owner/repo" format


def create_jwt_token(user_id: str) -> str:
    """Create a JWT token for the user."""
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[str]:
    """Decode JWT token and return user_id."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token in cookie or Authorization header.
    """
    # Try cookie first
    token = request.cookies.get("vam_auth_token")
    
    # Fall back to Authorization header
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
    
    if not token:
        return None
    
    user_id = decode_jwt_token(token)
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    return user


async def require_auth(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Require authenticated user."""
    user = await get_current_user(request, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# Store OAuth state tokens temporarily (in production, use Redis)
oauth_states: dict = {}


@router.get("/github")
async def github_oauth_redirect(
    redirect_to: Optional[str] = Query(None, description="URL to redirect after login")
):
    """
    Initiate GitHub OAuth flow.
    Redirects user to GitHub for authorization.
    """
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    oauth_states[state] = {
        "created_at": datetime.utcnow(),
        "redirect_to": redirect_to or "/"
    }
    
    # Clean old states (older than 10 minutes)
    now = datetime.utcnow()
    expired = [k for k, v in oauth_states.items() 
               if (now - v["created_at"]).seconds > 600]
    for k in expired:
        del oauth_states[k]
    
    oauth_url = github_service.get_oauth_url(state=state)
    return RedirectResponse(url=oauth_url)


@router.get("/callback/github")
async def github_oauth_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: str = Query(..., description="State parameter for CSRF verification"),
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Handle GitHub OAuth callback.
    Exchanges code for token and creates/updates user.
    """
    # Verify state
    state_data = oauth_states.pop(state, None)
    if not state_data:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    
    redirect_to = state_data.get("redirect_to", "/")
    
    try:
        # Exchange code for token
        token_data = await github_service.exchange_code_for_token(code)
        access_token = token_data.get("access_token")
        scope = token_data.get("scope", "")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Get user info from GitHub
        github_user = await github_service.get_user_info(access_token)
        github_id = str(github_user["id"])
        
        # Find or create user
        user = db.query(User).filter(User.github_id == github_id).first()
        
        if not user:
            # Try to find by email
            email = github_user.get("email") or f"{github_user['login']}@github.local"
            user = db.query(User).filter(User.email == email).first()
        
        if user:
            # Update existing user with GitHub info
            user.github_id = github_id
            user.github_username = github_user["login"]
            user.github_access_token = access_token
            user.github_token_scope = scope
            user.github_avatar_url = github_user.get("avatar_url")
            user.last_login = datetime.utcnow()
        else:
            # Create new user
            user = User(
                id=str(uuid.uuid4()),
                email=github_user.get("email") or f"{github_user['login']}@github.local",
                name=github_user.get("name") or github_user["login"],
                github_id=github_id,
                github_username=github_user["login"],
                github_access_token=access_token,
                github_token_scope=scope,
                github_avatar_url=github_user.get("avatar_url"),
                role=UserRole.CONTRIBUTOR,
                is_active=True,
                is_verified=True,  # GitHub verified
                last_login=datetime.utcnow()
            )
            db.add(user)
        
        db.commit()
        db.refresh(user)
        
        # Create JWT token
        jwt_token = create_jwt_token(user.id)
        
        # Redirect to frontend with token
        redirect_url = f"{FRONTEND_URL}{redirect_to}?auth_success=true"
        response = RedirectResponse(url=redirect_url)
        response.set_cookie(
            key="vam_auth_token",
            value=jwt_token,
            httponly=True,
            samesite="lax",
            max_age=JWT_EXPIRATION_HOURS * 3600
        )
        
        return response
        
    except Exception as e:
        # Redirect to frontend with error
        error_url = f"{FRONTEND_URL}/login?error={str(e)}"
        return RedirectResponse(url=error_url)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(require_auth)):
    """Get current authenticated user info."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value if user.role else "viewer",
        github_username=user.github_username,
        github_avatar_url=user.github_avatar_url,
        default_github_repo=user.default_github_repo,
        is_github_connected=bool(user.github_access_token)
    )


@router.post("/logout")
async def logout(response: Response):
    """Logout and clear session."""
    response.delete_cookie("vam_auth_token")
    return {"message": "Logged out successfully"}


@router.get("/repos", response_model=list[RepoResponse])
async def get_user_repos(user: User = Depends(require_auth)):
    """Get user's GitHub repositories for repo selection."""
    if not user.github_access_token:
        raise HTTPException(status_code=400, detail="GitHub not connected")
    
    try:
        repos = await github_service.get_user_repos(user.github_access_token)
        return [
            RepoResponse(
                id=repo["id"],
                full_name=repo["full_name"],
                name=repo["name"],
                private=repo["private"],
                description=repo.get("description"),
                html_url=repo["html_url"]
            )
            for repo in repos
            if repo.get("permissions", {}).get("push", False)  # Only repos user can push to
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repos: {str(e)}")


@router.post("/set-default-repo")
async def set_default_repo(
    request: SetDefaultRepoRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Set user's default GitHub repository for task sync."""
    user.default_github_repo = request.repo
    db.commit()
    return {"message": f"Default repo set to {request.repo}"}


@router.get("/status")
async def auth_status(request: Request, db: Session = Depends(get_db)):
    """Check authentication status without requiring auth."""
    user = await get_current_user(request, db)
    
    if user:
        return {
            "authenticated": True,
            "user": UserResponse(
                id=user.id,
                email=user.email,
                name=user.name,
                role=user.role.value if user.role else "viewer",
                github_username=user.github_username,
                github_avatar_url=user.github_avatar_url,
                default_github_repo=user.default_github_repo,
                is_github_connected=bool(user.github_access_token)
            )
        }
    
    return {"authenticated": False, "user": None}
