"""
GitHub Service - GitHub API Integration for OAuth and Issue Management.

Provides:
- OAuth token exchange
- User profile fetching
- Issue creation, update, and status checking
"""

import os
import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GitHubService:
    """
    Service for interacting with GitHub API.
    Handles OAuth flow and issue management.
    """
    
    GITHUB_API_BASE = "https://api.github.com"
    GITHUB_OAUTH_URL = "https://github.com/login/oauth/authorize"
    GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
    
    def __init__(self):
        self.client_id = os.getenv("GITHUB_CLIENT_ID", "")
        self.client_secret = os.getenv("GITHUB_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv(
            "GITHUB_REDIRECT_URI", 
            "http://localhost:8000/auth/callback/github"
        )
        self.default_repo = os.getenv("GITHUB_DEFAULT_REPO", "")
        self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    
    def get_oauth_url(self, state: Optional[str] = None) -> str:
        """
        Generate GitHub OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Full OAuth URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "repo user:email",  # Request repo and email access
            "allow_signup": "true"
        }
        if state:
            params["state"] = state
        
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.GITHUB_OAUTH_URL}?{query}"
    
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange OAuth authorization code for access token.
        
        Args:
            code: Authorization code from GitHub callback
            
        Returns:
            Token response with access_token, scope, token_type
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.GITHUB_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri
                },
                headers={"Accept": "application/json"}
            )
            
            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise Exception(f"Failed to exchange code for token: {response.text}")
            
            data = response.json()
            
            if "error" in data:
                logger.error(f"OAuth error: {data}")
                raise Exception(f"OAuth error: {data.get('error_description', data['error'])}")
            
            return data
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch GitHub user profile information.
        
        Args:
            access_token: Valid GitHub access token
            
        Returns:
            User profile with id, login, email, avatar_url, etc.
        """
        async with httpx.AsyncClient() as client:
            # Get user profile
            response = await client.get(
                f"{self.GITHUB_API_BASE}/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch user info: {response.text}")
                raise Exception(f"Failed to fetch user info: {response.text}")
            
            user_data = response.json()
            
            # Get user's primary email if not public
            if not user_data.get("email"):
                email_response = await client.get(
                    f"{self.GITHUB_API_BASE}/user/emails",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Accept": "application/vnd.github.v3+json"
                    }
                )
                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_email = next(
                        (e["email"] for e in emails if e.get("primary")), 
                        None
                    )
                    if primary_email:
                        user_data["email"] = primary_email
            
            return user_data
    
    async def get_user_repos(
        self, 
        access_token: str, 
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Fetch user's repositories.
        
        Args:
            access_token: Valid GitHub access token
            per_page: Number of repos to fetch
            
        Returns:
            List of repository objects
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GITHUB_API_BASE}/user/repos",
                params={
                    "sort": "updated",
                    "per_page": per_page,
                    "affiliation": "owner,collaborator"
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch repos: {response.text}")
                raise Exception(f"Failed to fetch repos: {response.text}")
            
            return response.json()
    
    async def create_issue(
        self,
        access_token: str,
        repo: str,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new issue in a GitHub repository.
        
        Args:
            access_token: Valid GitHub access token
            repo: Repository in "owner/repo" format
            title: Issue title
            body: Issue body/description
            labels: Optional list of labels
            assignees: Optional list of GitHub usernames to assign
            
        Returns:
            Created issue object with id, number, html_url, etc.
        """
        payload = {
            "title": title,
            "body": body
        }
        if labels:
            payload["labels"] = labels
        if assignees:
            payload["assignees"] = assignees
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.GITHUB_API_BASE}/repos/{repo}/issues",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create issue: {response.text}")
                raise Exception(f"Failed to create issue: {response.text}")
            
            issue = response.json()
            logger.info(f"Created GitHub issue #{issue['number']} in {repo}")
            return issue
    
    async def get_issue(
        self,
        access_token: str,
        repo: str,
        issue_number: int
    ) -> Dict[str, Any]:
        """
        Fetch a specific issue from a repository.
        
        Args:
            access_token: Valid GitHub access token
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            
        Returns:
            Issue object with current state
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.GITHUB_API_BASE}/repos/{repo}/issues/{issue_number}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch issue: {response.text}")
                raise Exception(f"Failed to fetch issue: {response.text}")
            
            return response.json()
    
    async def update_issue(
        self,
        access_token: str,
        repo: str,
        issue_number: int,
        title: Optional[str] = None,
        body: Optional[str] = None,
        state: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing issue.
        
        Args:
            access_token: Valid GitHub access token
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            title: New title (optional)
            body: New body (optional)
            state: "open" or "closed" (optional)
            labels: New labels (optional)
            
        Returns:
            Updated issue object
        """
        payload = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if state is not None:
            payload["state"] = state
        if labels is not None:
            payload["labels"] = labels
        
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.GITHUB_API_BASE}/repos/{repo}/issues/{issue_number}",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to update issue: {response.text}")
                raise Exception(f"Failed to update issue: {response.text}")
            
            return response.json()
    
    async def close_issue(
        self,
        access_token: str,
        repo: str,
        issue_number: int
    ) -> Dict[str, Any]:
        """
        Close an issue.
        
        Args:
            access_token: Valid GitHub access token
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            
        Returns:
            Updated issue object
        """
        return await self.update_issue(
            access_token=access_token,
            repo=repo,
            issue_number=issue_number,
            state="closed"
        )
    
    async def add_issue_comment(
        self,
        access_token: str,
        repo: str,
        issue_number: int,
        body: str
    ) -> Dict[str, Any]:
        """
        Add a comment to an issue.
        
        Args:
            access_token: Valid GitHub access token
            repo: Repository in "owner/repo" format
            issue_number: Issue number
            body: Comment body
            
        Returns:
            Created comment object
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.GITHUB_API_BASE}/repos/{repo}/issues/{issue_number}/comments",
                json={"body": body},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to add comment: {response.text}")
                raise Exception(f"Failed to add comment: {response.text}")
            
            return response.json()
    
    def verify_webhook_signature(
        self, 
        payload: bytes, 
        signature: str
    ) -> bool:
        """
        Verify GitHub webhook signature for security.
        
        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
            
        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib
        
        if not self.webhook_secret:
            logger.warning("No webhook secret configured, skipping verification")
            return True
        
        expected_signature = "sha256=" + hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)


# Singleton instance
github_service = GitHubService()
