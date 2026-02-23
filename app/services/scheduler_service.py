"""
Scheduler Service

Manages scheduled reminder jobs using APScheduler.
"""
from datetime import datetime
from typing import Optional

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.models.reminder_schemas import ScheduleConfig
from app.services.reminder_config_service import reminder_config_service
from app.constants.reminder_constants import DAYS_OF_WEEK

logger = structlog.get_logger()


class ReminderSchedulerService:
    """Service for managing scheduled reminder jobs"""
    
    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.job_id = "payment_reminder_job"
        self.is_running = False
    
    async def initialize(self):
        """Initialize and start the scheduler if enabled"""
        logger.info("initializing_scheduler")
        
        # Create scheduler
        self.scheduler = AsyncIOScheduler()
        
        # Load config
        config = reminder_config_service.get_config()
        
        if config.schedule.enabled:
            await self._schedule_job(config.schedule)
            self.scheduler.start()
            self.is_running = True
            logger.info(
                "scheduler_started",
                frequency=config.schedule.frequency,
                day=DAYS_OF_WEEK.get(config.schedule.day_of_week, "Unknown"),
                time=config.schedule.time
            )
        else:
            logger.info("scheduler_disabled_in_config")
    
    async def _schedule_job(self, schedule: ScheduleConfig):
        """Schedule the reminder job"""
        hour, minute = map(int, schedule.time.split(':'))
        
        if schedule.frequency == "weekly":
            # Weekly on specific day
            trigger = CronTrigger(
                day_of_week=schedule.day_of_week,
                hour=hour,
                minute=minute,
                timezone=schedule.timezone
            )
        elif schedule.frequency == "biweekly":
            # Bi-weekly (every 2 weeks on specific day)
            # APScheduler doesn't have direct bi-weekly, so we use weekly
            # and check in the job if it's the right week
            trigger = CronTrigger(
                day_of_week=schedule.day_of_week,
                hour=hour,
                minute=minute,
                timezone=schedule.timezone
            )
        else:
            raise ValueError(f"Invalid frequency: {schedule.frequency}")
        
        # Add job
        self.scheduler.add_job(
            self._run_scheduled_reminders,
            trigger=trigger,
            id=self.job_id,
            replace_existing=True,
            misfire_grace_time=3600  # 1 hour grace period
        )
        
        logger.info(
            "job_scheduled",
            frequency=schedule.frequency,
            day_of_week=schedule.day_of_week,
            time=schedule.time
        )
    
    async def _run_scheduled_reminders(self):
        """Job callback - runs scheduled reminders"""
        logger.info("running_scheduled_reminders")
        
        try:
            # Import here to avoid circular dependency
            from app.services.reminder_service import reminder_service
            
            # Check if bi-weekly and correct week
            config = reminder_config_service.get_config()
            if config.schedule.frequency == "biweekly":
                # Check if this is an even week (bi-weekly)
                current_week = datetime.now().isocalendar()[1]
                if current_week % 2 != 0:
                    logger.info("skipping_biweekly_reminder_odd_week", week=current_week)
                    return
            
            # Get all enabled parties
            eligible_parties = await reminder_service.get_eligible_parties()
            enabled_parties = [p for p in eligible_parties if p.permanent_enabled]
            
            if not enabled_parties:
                logger.info("no_enabled_parties_for_scheduled_reminders")
                return
            
            party_codes = [p.code for p in enabled_parties]
            
            # Get active template
            template = reminder_config_service.get_active_template()
            
            # Send reminders
            await reminder_service.send_reminders_to_parties(
                party_codes=party_codes,
                template_id=template.id,
                sent_by="scheduler"
            )
            
            logger.info(
                "scheduled_reminders_completed",
                party_count=len(party_codes),
                template_id=template.id
            )
            
        except Exception as e:
            logger.error(
                "scheduled_reminders_failed",
                error=str(e),
                exc_info=True
            )
    
    async def start_scheduler(self):
        """Start the scheduler"""
        if self.scheduler is None:
            await self.initialize()
            return
        
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            logger.info("scheduler_started_manually")
    
    async def stop_scheduler(self):
        """Stop the scheduler"""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("scheduler_stopped")
    
    async def pause_scheduler(self):
        """Pause the scheduler (keeps jobs but stops execution)"""
        if self.scheduler and self.is_running:
            self.scheduler.pause()
            logger.info("scheduler_paused")
    
    async def resume_scheduler(self):
        """Resume a paused scheduler"""
        if self.scheduler:
            self.scheduler.resume()
            logger.info("scheduler_resumed")
    
    async def trigger_manual_run(self) -> str:
        """
        Manually trigger a reminder run
        
        Returns:
            Batch ID of the triggered run
        """
        logger.info("manual_reminder_run_triggered")
        
        try:
            from app.services.reminder_service import reminder_service
            
            # Get all enabled parties
            eligible_parties = await reminder_service.get_eligible_parties()
            enabled_parties = [p for p in eligible_parties if p.permanent_enabled]
            
            if not enabled_parties:
                logger.warning("no_enabled_parties_for_manual_run")
                raise ValueError("No parties are enabled for reminders")
            
            party_codes = [p.code for p in enabled_parties]
            template = reminder_config_service.get_active_template()
            
            # Send reminders
            batch_id = await reminder_service.send_reminders_to_parties(
                party_codes=party_codes,
                template_id=template.id,
                sent_by="manual"
            )
            
            logger.info(
                "manual_reminders_completed",
                batch_id=batch_id,
                party_count=len(party_codes)
            )
            
            return batch_id
            
        except Exception as e:
            logger.error(
                "manual_reminders_failed",
                error=str(e),
                exc_info=True
            )
            raise
    
    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time"""
        if self.scheduler and self.is_running:
            job = self.scheduler.get_job(self.job_id)
            if job:
                return job.next_run_time
        return None
    
    def get_status(self) -> dict:
        """Get current scheduler status"""
        return {
            "is_running": self.is_running,
            "next_run": self.get_next_run_time(),
            "job_id": self.job_id,
        }


# Global instance
scheduler_service = ReminderSchedulerService()
