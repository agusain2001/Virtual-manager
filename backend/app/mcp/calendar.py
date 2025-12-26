"""
MCP Calendar Module - Calendar integration for VAM.

Provides calendar capabilities:
- fetch_daily_schedule: Get events and free slots for a day
- schedule_focus_block: Create focus time blocks
- move_flexible_meeting: Reschedule flexible events
- list_events: Raw event listing
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

# Logging
try:
    from app.core.logging import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


async def fetch_daily_schedule(
    user_id: str,
    date: datetime,
    db: Session
) -> Dict[str, Any]:
    """
    Fetch the daily schedule for a user from Google Calendar.
    
    Args:
        user_id: User ID to fetch schedule for
        date: Date to get schedule for
        db: Database session
    
    Returns:
        Dict with events, free slots, and busy hours
    """
    try:
        from app.services.google_calendar_service import get_calendar_service
    except ImportError:
        from backend.app.services.google_calendar_service import get_calendar_service
    
    service = await get_calendar_service(user_id, db)
    
    if not service:
        logger.warning(f"User {user_id} does not have Google Calendar connected")
        return {
            "connected": False,
            "error": "Google Calendar not connected",
            "events": [],
            "free_slots": []
        }
    
    try:
        schedule = await service.get_daily_schedule(date)
        schedule["connected"] = True
        
        logger.info(f"Fetched schedule for user {user_id}: {len(schedule['events'])} events")
        return schedule
        
    except Exception as e:
        logger.error(f"Error fetching schedule for user {user_id}: {e}")
        return {
            "connected": True,
            "error": str(e),
            "events": [],
            "free_slots": []
        }


async def schedule_focus_block(
    user_id: str,
    task_title: str,
    start_time: datetime,
    duration_minutes: int,
    db: Session
) -> Dict[str, Any]:
    """
    Schedule a focus block on the user's calendar.
    
    Args:
        user_id: User ID
        task_title: Title of the task to focus on
        start_time: When to start the focus block
        duration_minutes: Duration in minutes
        db: Database session
    
    Returns:
        Created event info or error
    """
    try:
        from app.services.google_calendar_service import get_calendar_service
    except ImportError:
        from backend.app.services.google_calendar_service import get_calendar_service
    
    service = await get_calendar_service(user_id, db)
    
    if not service:
        return {
            "success": False,
            "error": "Google Calendar not connected"
        }
    
    try:
        result = await service.schedule_focus_block(
            task_title=task_title,
            start_time=start_time,
            duration_minutes=duration_minutes
        )
        
        if result.get("error"):
            return {
                "success": False,
                "error": result.get("message")
            }
        
        logger.info(f"Scheduled focus block for user {user_id}: {task_title}")
        return {
            "success": True,
            "event_id": result.get("id"),
            "summary": result.get("summary"),
            "start": start_time.isoformat(),
            "end": (start_time + timedelta(minutes=duration_minutes)).isoformat(),
            "html_link": result.get("html_link")
        }
        
    except Exception as e:
        logger.error(f"Error scheduling focus block for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def move_flexible_meeting(
    user_id: str,
    event_id: str,
    new_start: datetime,
    new_end: datetime,
    db: Session
) -> Dict[str, Any]:
    """
    Move a flexible meeting to a new time.
    Only works for events marked as flexible (created by VAM).
    
    Args:
        user_id: User ID
        event_id: Google Calendar event ID
        new_start: New start time
        new_end: New end time
        db: Database session
    
    Returns:
        Updated event info or error
    """
    try:
        from app.services.google_calendar_service import get_calendar_service
    except ImportError:
        from backend.app.services.google_calendar_service import get_calendar_service
    
    service = await get_calendar_service(user_id, db)
    
    if not service:
        return {
            "success": False,
            "error": "Google Calendar not connected"
        }
    
    try:
        result = await service.move_event(
            event_id=event_id,
            new_start=new_start,
            new_end=new_end
        )
        
        if result.get("error"):
            return {
                "success": False,
                "error": result.get("message")
            }
        
        logger.info(f"Moved event {event_id} for user {user_id}")
        return {
            "success": True,
            "event_id": event_id,
            "new_start": new_start.isoformat(),
            "new_end": new_end.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error moving event for user {user_id}: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def find_free_slot(
    user_id: str,
    date: datetime,
    duration_minutes: int,
    db: Session,
    preferred_start_hour: int = 9,
    preferred_end_hour: int = 18
) -> Optional[Dict[str, Any]]:
    """
    Find the next available free slot of specified duration.
    
    Args:
        user_id: User ID
        date: Date to search for free slots
        duration_minutes: Required duration in minutes
        db: Database session
        preferred_start_hour: Earliest hour to consider (default 9 AM)
        preferred_end_hour: Latest hour to consider (default 6 PM)
    
    Returns:
        Free slot info or None if no slot available
    """
    schedule = await fetch_daily_schedule(user_id, date, db)
    
    if not schedule.get("connected"):
        return None
    
    for slot in schedule.get("free_slots", []):
        if slot.get("duration_minutes", 0) >= duration_minutes:
            slot_start = datetime.fromisoformat(slot["start"])
            
            # Check if within preferred hours
            if preferred_start_hour <= slot_start.hour < preferred_end_hour:
                return {
                    "start": slot["start"],
                    "end": slot["end"],
                    "duration_minutes": slot["duration_minutes"]
                }
    
    return None


# Legacy functions for backward compatibility
def list_events(day: str) -> List[str]:
    """
    DEPRECATED: Use fetch_daily_schedule instead.
    Legacy function for listing events (returns mock data).
    """
    logger.warning("list_events is deprecated. Use fetch_daily_schedule instead.")
    return ["Daily Standup at 10:00 AM", "Client Review at 2:00 PM"]


def add_event(title: str, time: str) -> str:
    """
    DEPRECATED: Use schedule_focus_block instead.
    Legacy function for adding events (returns mock response).
    """
    logger.warning("add_event is deprecated. Use schedule_focus_block instead.")
    return "Event Created"
