"""
Scheduler - Daily snapshot and automation tasks.

Provides APScheduler-based background jobs for:
- Daily project snapshots
- Automation rule evaluation
- Morning standup (Phase 2)
"""

from datetime import datetime
from typing import Optional
import asyncio


def daily_snapshot_job():
    """Take snapshots of all active projects at midnight."""
    from backend.app.core.database import SessionLocal
    from backend.app.core.analytics import take_project_snapshot
    from backend.app.models import Project
    
    db = SessionLocal()
    try:
        projects = db.query(Project).all()
        for project in projects:
            take_project_snapshot(db, project.id)
        print(f"[Scheduler] Captured snapshots for {len(projects)} projects at {datetime.utcnow()}")
    except Exception as e:
        print(f"[Scheduler] Error taking snapshots: {e}")
    finally:
        db.close()


def morning_standup_job():
    """
    Trigger morning standup for all users at 09:00 local time.
    
    This job:
    1. Gets all users with Slack linked
    2. Fetches their GitHub issues
    3. Sends standup prompt via Slack DM
    """
    try:
        from backend.app.core.database import SessionLocal
        from backend.app.agents.standup_handler import trigger_standup_for_all_users
    except ImportError:
        from app.core.database import SessionLocal
        from app.agents.standup_handler import trigger_standup_for_all_users
    
    db = SessionLocal()
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(trigger_standup_for_all_users(db))
            print(f"[Scheduler] Morning standup: {result['success']}/{result['total']} users notified")
        finally:
            loop.close()
    except Exception as e:
        print(f"[Scheduler] Error running morning standup: {e}")
    finally:
        db.close()


def start_scheduler():
    """
    Start the background scheduler.
    
    Note: Requires APScheduler to be installed.
    Install with: pip install apscheduler
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = BackgroundScheduler()
        
        # Daily at midnight - snapshots
        scheduler.add_job(
            daily_snapshot_job,
            CronTrigger(hour=0, minute=0),
            id='daily_snapshot',
            name='Daily Project Snapshots',
            replace_existing=True
        )
        
        # Daily at 9 AM - morning standup
        scheduler.add_job(
            morning_standup_job,
            CronTrigger(hour=9, minute=0),
            id='morning_standup',
            name='Morning Standup',
            replace_existing=True
        )
        
        scheduler.start()
        print("[Scheduler] Started background scheduler with jobs:")
        print("  - Daily Snapshot (00:00)")
        print("  - Morning Standup (09:00)")
        return scheduler
    except ImportError:
        print("[Scheduler] APScheduler not installed. Run: pip install apscheduler")
        return None


def run_snapshot_now():
    """Manually trigger snapshot job (for testing)."""
    daily_snapshot_job()
    return {"status": "completed", "timestamp": datetime.utcnow().isoformat()}


def run_standup_now():
    """Manually trigger standup job (for testing)."""
    morning_standup_job()
    return {"status": "completed", "timestamp": datetime.utcnow().isoformat()}

