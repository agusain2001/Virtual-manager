"""
Google Calendar Service - Real Google Calendar API integration.

Provides:
- Token refresh handling
- List calendar events
- Create calendar events (focus blocks)
- Update/move events
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx

# Logging
try:
    from app.core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")


class GoogleCalendarService:
    """Service for interacting with Google Calendar API."""
    
    BASE_URL = "https://www.googleapis.com/calendar/v3"
    
    def __init__(self, access_token: str, refresh_token: Optional[str] = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._token_refreshed = False
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def _refresh_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self.refresh_token or self._token_refreshed:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": GOOGLE_CLIENT_ID,
                        "client_secret": GOOGLE_CLIENT_SECRET,
                        "refresh_token": self.refresh_token,
                        "grant_type": "refresh_token",
                    }
                )
                
                if response.status_code == 200:
                    tokens = response.json()
                    self.access_token = tokens.get("access_token")
                    self._token_refreshed = True
                    return True
                    
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
        
        return False
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make an authenticated request to Google Calendar API."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = await self._get_headers()
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data, params=params)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=data)
            elif method == "PATCH":
                response = await client.patch(url, headers=headers, json=data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            # If unauthorized, try to refresh token and retry
            if response.status_code == 401 and not self._token_refreshed:
                if await self._refresh_token():
                    headers = await self._get_headers()
                    if method == "GET":
                        response = await client.get(url, headers=headers, params=params)
                    elif method == "POST":
                        response = await client.post(url, headers=headers, json=data, params=params)
                    elif method == "PUT":
                        response = await client.put(url, headers=headers, json=data)
                    elif method == "PATCH":
                        response = await client.patch(url, headers=headers, json=data)
            
            if response.status_code >= 400:
                error_detail = response.text
                logger.error(f"Google Calendar API error: {response.status_code} - {error_detail}")
                return {"error": True, "status_code": response.status_code, "detail": error_detail}
            
            return response.json() if response.text else {}
    
    async def list_calendars(self) -> List[Dict[str, Any]]:
        """List all calendars the user has access to."""
        result = await self._make_request("GET", "/users/me/calendarList")
        
        if result.get("error"):
            return []
        
        return result.get("items", [])
    
    async def get_events(
        self,
        calendar_id: str = "primary",
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 50,
        single_events: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get calendar events for a date range.
        
        Args:
            calendar_id: Calendar ID (default: primary)
            time_min: Start of time range
            time_max: End of time range
            max_results: Maximum number of events
            single_events: Expand recurring events
        
        Returns:
            List of calendar events
        """
        if time_min is None:
            time_min = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if time_max is None:
            time_max = time_min + timedelta(days=1)
        
        params = {
            "timeMin": time_min.isoformat() + "Z",
            "timeMax": time_max.isoformat() + "Z",
            "maxResults": max_results,
            "singleEvents": str(single_events).lower(),
            "orderBy": "startTime"
        }
        
        result = await self._make_request("GET", f"/calendars/{calendar_id}/events", params=params)
        
        if result.get("error"):
            return []
        
        return result.get("items", [])
    
    async def get_daily_schedule(
        self,
        date: datetime,
        calendar_id: str = "primary",
        include_transparent: bool = False
    ) -> Dict[str, Any]:
        """
        Get the daily schedule with free time slots.
        
        Args:
            date: The date to get schedule for
            calendar_id: Calendar ID
            include_transparent: Include "transparent" events (show as free)
        
        Returns:
            Dict with events and free slots
        """
        time_min = date.replace(hour=0, minute=0, second=0, microsecond=0)
        time_max = time_min + timedelta(days=1)
        
        events = await self.get_events(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max
        )
        
        # Filter out transparent events (holidays, all-day events marked as "free")
        busy_events = []
        for event in events:
            # Skip cancelled events
            if event.get("status") == "cancelled":
                continue
                
            # Skip transparent events unless requested
            if not include_transparent and event.get("transparency") == "transparent":
                continue
            
            # Parse event times
            start = event.get("start", {})
            end = event.get("end", {})
            
            # Handle all-day events
            if "date" in start:
                event_start = datetime.fromisoformat(start["date"])
                event_end = datetime.fromisoformat(end["date"])
                is_all_day = True
            else:
                event_start = datetime.fromisoformat(start.get("dateTime", "").replace("Z", "+00:00"))
                event_end = datetime.fromisoformat(end.get("dateTime", "").replace("Z", "+00:00"))
                is_all_day = False
            
            busy_events.append({
                "id": event.get("id"),
                "summary": event.get("summary", "Busy"),
                "start": event_start.isoformat(),
                "end": event_end.isoformat(),
                "is_all_day": is_all_day,
                "is_flexible": "vam-flexible" in event.get("description", "").lower(),
                "html_link": event.get("htmlLink")
            })
        
        # Calculate free slots (simplified - assumes 9 AM to 6 PM work hours)
        work_start = time_min.replace(hour=9, minute=0)
        work_end = time_min.replace(hour=18, minute=0)
        
        free_slots = self._calculate_free_slots(busy_events, work_start, work_end)
        
        return {
            "date": date.isoformat(),
            "events": busy_events,
            "free_slots": free_slots,
            "total_busy_hours": sum(
                (datetime.fromisoformat(e["end"]) - datetime.fromisoformat(e["start"])).total_seconds() / 3600
                for e in busy_events if not e["is_all_day"]
            )
        }
    
    def _calculate_free_slots(
        self,
        events: List[Dict],
        work_start: datetime,
        work_end: datetime
    ) -> List[Dict[str, str]]:
        """Calculate free time slots between events."""
        free_slots = []
        current_time = work_start
        
        # Sort events by start time
        sorted_events = sorted(
            [e for e in events if not e["is_all_day"]],
            key=lambda x: x["start"]
        )
        
        for event in sorted_events:
            event_start = datetime.fromisoformat(event["start"])
            
            # Skip events outside work hours
            if event_start > work_end:
                break
            
            # Add free slot if there's a gap
            if event_start > current_time:
                free_slots.append({
                    "start": current_time.isoformat(),
                    "end": event_start.isoformat(),
                    "duration_minutes": int((event_start - current_time).total_seconds() / 60)
                })
            
            # Update current time
            event_end = datetime.fromisoformat(event["end"])
            if event_end > current_time:
                current_time = event_end
        
        # Add final free slot if there's time left
        if current_time < work_end:
            free_slots.append({
                "start": current_time.isoformat(),
                "end": work_end.isoformat(),
                "duration_minutes": int((work_end - current_time).total_seconds() / 60)
            })
        
        return free_slots
    
    async def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        description: Optional[str] = None,
        calendar_id: str = "primary",
        attendees: Optional[List[str]] = None,
        is_flexible: bool = False
    ) -> Dict[str, Any]:
        """
        Create a calendar event.
        
        Args:
            summary: Event title
            start_time: Event start time
            end_time: Event end time
            description: Event description
            calendar_id: Calendar to create event in
            attendees: List of attendee emails
            is_flexible: Mark event as flexible (can be moved by VAM)
        
        Returns:
            Created event data
        """
        event_data = {
            "summary": summary,
            "start": {
                "dateTime": start_time.isoformat(),
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "UTC"
            }
        }
        
        if description:
            event_data["description"] = description
        
        if is_flexible:
            # Add marker that VAM can move this event
            event_data["description"] = (event_data.get("description", "") + 
                                         "\n\n[vam-flexible] This event can be rescheduled by VAM.").strip()
        
        if attendees:
            event_data["attendees"] = [{"email": email} for email in attendees]
        
        result = await self._make_request(
            "POST",
            f"/calendars/{calendar_id}/events",
            data=event_data
        )
        
        if result.get("error"):
            logger.error(f"Failed to create event: {result}")
            return {"error": True, "message": result.get("detail")}
        
        logger.info(f"Created calendar event: {summary}")
        return {
            "id": result.get("id"),
            "summary": result.get("summary"),
            "start": result.get("start"),
            "end": result.get("end"),
            "html_link": result.get("htmlLink")
        }
    
    async def schedule_focus_block(
        self,
        task_title: str,
        start_time: datetime,
        duration_minutes: int = 120,
        calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """
        Schedule a focus block for working on a task.
        
        Args:
            task_title: Title of the task
            start_time: When to start the focus block
            duration_minutes: Duration in minutes
            calendar_id: Calendar to use
        
        Returns:
            Created event info
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        return await self.create_event(
            summary=f"🎯 Focus: {task_title}",
            start_time=start_time,
            end_time=end_time,
            description=f"Focus time blocked by VAM for working on: {task_title}",
            calendar_id=calendar_id,
            is_flexible=True
        )
    
    async def update_event(
        self,
        event_id: str,
        updates: Dict[str, Any],
        calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Update an existing calendar event."""
        result = await self._make_request(
            "PATCH",
            f"/calendars/{calendar_id}/events/{event_id}",
            data=updates
        )
        
        if result.get("error"):
            return {"error": True, "message": result.get("detail")}
        
        return result
    
    async def move_event(
        self,
        event_id: str,
        new_start: datetime,
        new_end: datetime,
        calendar_id: str = "primary"
    ) -> Dict[str, Any]:
        """Move an event to a new time."""
        return await self.update_event(
            event_id=event_id,
            updates={
                "start": {"dateTime": new_start.isoformat(), "timeZone": "UTC"},
                "end": {"dateTime": new_end.isoformat(), "timeZone": "UTC"}
            },
            calendar_id=calendar_id
        )
    
    async def delete_event(
        self,
        event_id: str,
        calendar_id: str = "primary"
    ) -> bool:
        """Delete a calendar event."""
        result = await self._make_request(
            "DELETE",
            f"/calendars/{calendar_id}/events/{event_id}"
        )
        
        return not result.get("error", False)


# Singleton instance factory
_service_cache: Dict[str, GoogleCalendarService] = {}


async def get_calendar_service(
    user_id: str,
    db_session
) -> Optional[GoogleCalendarService]:
    """
    Get a GoogleCalendarService for a user.
    
    Args:
        user_id: User ID
        db_session: Database session
    
    Returns:
        GoogleCalendarService instance or None if not connected
    """
    try:
        from app.models import UserIntegration
    except ImportError:
        from backend.app.models import UserIntegration
    
    integration = db_session.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.provider == "google",
        UserIntegration.is_active == True
    ).first()
    
    if not integration or not integration.access_token:
        return None
    
    return GoogleCalendarService(
        access_token=integration.access_token,
        refresh_token=integration.refresh_token
    )
