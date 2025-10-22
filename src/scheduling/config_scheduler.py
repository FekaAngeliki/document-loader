"""
Config-Based Scheduling System

Reads scheduling configuration from knowledge base config files and
manages automated sync operations based on specified frequencies and times.
"""

import asyncio
import json
from datetime import datetime, timedelta, time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from croniter import croniter
import structlog

from ..data.database import Database, DatabaseConfig
from ..admin.config_manager import create_config_manager

logger = structlog.get_logger(__name__)


@dataclass
class ScheduleConfig:
    """Schedule configuration from config file."""
    config_name: str
    enabled: bool
    frequency: str  # daily, weekly, hourly, cron
    time: Optional[str] = None  # HH:MM format for daily/weekly
    cron_expression: Optional[str] = None  # For custom cron schedules
    timezone: str = "UTC"
    max_duration_hours: int = 4
    retry_attempts: int = 3
    notification_emails: List[str] = None
    
    def __post_init__(self):
        if self.notification_emails is None:
            self.notification_emails = []


@dataclass
class ScheduleExecution:
    """Represents a scheduled execution."""
    config_name: str
    scheduled_time: datetime
    execution_id: str
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ConfigBasedScheduler:
    """Manages scheduling based on configuration files."""
    
    def __init__(self):
        self.running = False
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.executions: Dict[str, ScheduleExecution] = {}
    
    async def load_schedules_from_configs(self) -> None:
        """Load scheduling configuration from all active config files."""
        try:
            config_manager = await create_config_manager()
            configs = await config_manager.list_configs(status="active")
            
            logger.info(f"Loading schedules from {len(configs)} configurations")
            
            for config in configs:
                try:
                    config_data = json.loads(config['config_content']) if isinstance(config['config_content'], str) else config['config_content']
                    schedule_config = self._extract_schedule_config(config['name'], config_data)
                    
                    if schedule_config and schedule_config.enabled:
                        self.schedules[config['name']] = schedule_config
                        logger.info(f"Loaded schedule for {config['name']}: {schedule_config.frequency}")
                    
                except Exception as e:
                    logger.error(f"Failed to load schedule for config {config['name']}: {e}")
            
            await config_manager.db.disconnect()
            logger.info(f"Loaded {len(self.schedules)} active schedules")
            
        except Exception as e:
            logger.error(f"Failed to load schedules: {e}")
    
    def _extract_schedule_config(self, config_name: str, config_data: Dict[str, Any]) -> Optional[ScheduleConfig]:
        """Extract schedule configuration from config data."""
        
        # Look for schedule configuration in various locations
        schedule_data = None
        
        # Check top-level schedule
        if 'schedule' in config_data:
            schedule_data = config_data['schedule']
        
        # Check in sync_config
        elif 'sync_config' in config_data and 'schedule' in config_data['sync_config']:
            schedule_data = config_data['sync_config']['schedule']
        
        # Check for legacy scheduling fields
        elif any(key in config_data for key in ['sync_frequency', 'sync_time', 'auto_sync']):
            schedule_data = {
                'enabled': config_data.get('auto_sync', False),
                'frequency': config_data.get('sync_frequency', 'manual'),
                'time': config_data.get('sync_time'),
            }
        
        if not schedule_data:
            return None
        
        # Create schedule config
        try:
            return ScheduleConfig(
                config_name=config_name,
                enabled=schedule_data.get('enabled', False),
                frequency=schedule_data.get('frequency', 'manual'),
                time=schedule_data.get('time'),
                cron_expression=schedule_data.get('cron_expression'),
                timezone=schedule_data.get('timezone', 'UTC'),
                max_duration_hours=schedule_data.get('max_duration_hours', 4),
                retry_attempts=schedule_data.get('retry_attempts', 3),
                notification_emails=schedule_data.get('notification_emails', [])
            )
        except Exception as e:
            logger.error(f"Invalid schedule configuration for {config_name}: {e}")
            return None
    
    async def start_scheduler(self) -> None:
        """Start the scheduler main loop."""
        self.running = True
        logger.info("Starting config-based scheduler")
        
        while self.running:
            try:
                # Reload schedules every hour to pick up changes
                if datetime.now().minute == 0:
                    await self.load_schedules_from_configs()
                
                # Check for scheduled executions
                await self._check_scheduled_executions()
                
                # Clean up old executions
                await self._cleanup_old_executions()
                
                # Wait 1 minute before next check
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(60)  # Continue after error
    
    def stop_scheduler(self) -> None:
        """Stop the scheduler."""
        self.running = False
        logger.info("Stopping config-based scheduler")
    
    async def _check_scheduled_executions(self) -> None:
        """Check if any schedules should be executed now."""
        current_time = datetime.now()
        
        for config_name, schedule in self.schedules.items():
            try:
                if self._should_execute_now(schedule, current_time):
                    await self._schedule_execution(config_name, schedule, current_time)
            except Exception as e:
                logger.error(f"Error checking schedule for {config_name}: {e}")
    
    def _should_execute_now(self, schedule: ScheduleConfig, current_time: datetime) -> bool:
        """Determine if a schedule should execute now."""
        
        # Check if already running
        for execution in self.executions.values():
            if execution.config_name == schedule.config_name and execution.status == "running":
                return False
        
        # Check frequency-based scheduling
        if schedule.frequency == "hourly":
            return current_time.minute == 0
        
        elif schedule.frequency == "daily":
            if schedule.time:
                try:
                    schedule_time = time.fromisoformat(schedule.time)
                    return (current_time.hour == schedule_time.hour and 
                           current_time.minute == schedule_time.minute)
                except ValueError:
                    logger.error(f"Invalid time format for {schedule.config_name}: {schedule.time}")
                    return False
            else:
                # Default to midnight
                return current_time.hour == 0 and current_time.minute == 0
        
        elif schedule.frequency == "weekly":
            # Execute on Sundays by default, at specified time
            if current_time.weekday() == 6:  # Sunday
                if schedule.time:
                    try:
                        schedule_time = time.fromisoformat(schedule.time)
                        return (current_time.hour == schedule_time.hour and 
                               current_time.minute == schedule_time.minute)
                    except ValueError:
                        return False
                else:
                    return current_time.hour == 0 and current_time.minute == 0
        
        elif schedule.frequency == "cron" and schedule.cron_expression:
            try:
                cron = croniter(schedule.cron_expression, current_time - timedelta(minutes=1))
                next_time = cron.get_next(datetime)
                return abs((next_time - current_time).total_seconds()) < 60
            except Exception as e:
                logger.error(f"Invalid cron expression for {schedule.config_name}: {e}")
                return False
        
        return False
    
    async def _schedule_execution(self, config_name: str, schedule: ScheduleConfig, scheduled_time: datetime) -> None:
        """Schedule a sync execution."""
        import uuid
        
        execution_id = str(uuid.uuid4())
        execution = ScheduleExecution(
            config_name=config_name,
            scheduled_time=scheduled_time,
            execution_id=execution_id,
            status="pending"
        )
        
        self.executions[execution_id] = execution
        
        logger.info(f"Scheduling execution for {config_name} (ID: {execution_id})")
        
        # Execute in background
        asyncio.create_task(self._execute_sync(execution))
    
    async def _execute_sync(self, execution: ScheduleExecution) -> None:
        """Execute a scheduled sync operation."""
        
        execution.status = "running"
        execution.started_at = datetime.now()
        
        logger.info(f"Starting scheduled sync for {execution.config_name}")
        
        try:
            # Use CLI to execute sync
            import subprocess
            import os
            
            # Set up environment
            env = os.environ.copy()
            
            # Build CLI command
            cmd = [
                "python", "-m", "document_loader.cli",
                "multi-source", "sync-multi-kb",
                "--config-name", execution.config_name
            ]
            
            # Execute with timeout
            schedule = self.schedules.get(execution.config_name)
            timeout = schedule.max_duration_hours * 3600 if schedule else 14400  # 4 hours default
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            )
            
            if result.returncode == 0:
                execution.status = "completed"
                logger.info(f"Scheduled sync completed successfully for {execution.config_name}")
                
                # Send success notification if configured
                if schedule and schedule.notification_emails:
                    await self._send_notification(execution, "success")
            
            else:
                execution.status = "failed"
                execution.error_message = result.stderr
                logger.error(f"Scheduled sync failed for {execution.config_name}: {result.stderr}")
                
                # Send failure notification
                if schedule and schedule.notification_emails:
                    await self._send_notification(execution, "failure")
        
        except subprocess.TimeoutExpired:
            execution.status = "failed"
            execution.error_message = "Sync operation timed out"
            logger.error(f"Scheduled sync timed out for {execution.config_name}")
            
        except Exception as e:
            execution.status = "failed"
            execution.error_message = str(e)
            logger.error(f"Scheduled sync error for {execution.config_name}: {e}")
        
        finally:
            execution.completed_at = datetime.now()
    
    async def _send_notification(self, execution: ScheduleExecution, result_type: str) -> None:
        """Send notification about sync execution."""
        
        # TODO: Implement email notifications
        # For now, just log
        schedule = self.schedules.get(execution.config_name)
        if schedule and schedule.notification_emails:
            logger.info(f"Notification ({result_type}) sent for {execution.config_name} to {schedule.notification_emails}")
    
    async def _cleanup_old_executions(self) -> None:
        """Clean up execution records older than 7 days."""
        cutoff_time = datetime.now() - timedelta(days=7)
        
        to_remove = []
        for execution_id, execution in self.executions.items():
            if execution.completed_at and execution.completed_at < cutoff_time:
                to_remove.append(execution_id)
        
        for execution_id in to_remove:
            del self.executions[execution_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old execution records")
    
    def get_schedule_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            "running": self.running,
            "active_schedules": len(self.schedules),
            "pending_executions": len([e for e in self.executions.values() if e.status == "pending"]),
            "running_executions": len([e for e in self.executions.values() if e.status == "running"]),
            "schedules": {
                name: {
                    "frequency": schedule.frequency,
                    "time": schedule.time,
                    "enabled": schedule.enabled,
                    "next_execution": self._calculate_next_execution(schedule)
                }
                for name, schedule in self.schedules.items()
            }
        }
    
    def _calculate_next_execution(self, schedule: ScheduleConfig) -> Optional[str]:
        """Calculate the next execution time for a schedule."""
        try:
            current_time = datetime.now()
            
            if schedule.frequency == "hourly":
                next_time = current_time.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            
            elif schedule.frequency == "daily":
                if schedule.time:
                    schedule_time = time.fromisoformat(schedule.time)
                    next_time = current_time.replace(
                        hour=schedule_time.hour, 
                        minute=schedule_time.minute, 
                        second=0, 
                        microsecond=0
                    )
                    if next_time <= current_time:
                        next_time += timedelta(days=1)
                else:
                    next_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            
            elif schedule.frequency == "weekly":
                # Next Sunday
                days_until_sunday = (6 - current_time.weekday()) % 7
                if days_until_sunday == 0:
                    days_until_sunday = 7
                
                if schedule.time:
                    schedule_time = time.fromisoformat(schedule.time)
                    next_time = current_time.replace(
                        hour=schedule_time.hour,
                        minute=schedule_time.minute,
                        second=0,
                        microsecond=0
                    ) + timedelta(days=days_until_sunday)
                else:
                    next_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_until_sunday)
            
            elif schedule.frequency == "cron" and schedule.cron_expression:
                cron = croniter(schedule.cron_expression, current_time)
                next_time = cron.get_next(datetime)
            
            else:
                return None
            
            return next_time.isoformat()
        
        except Exception:
            return None


# Scheduler instance
_scheduler_instance = None


async def get_scheduler() -> ConfigBasedScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = ConfigBasedScheduler()
        await _scheduler_instance.load_schedules_from_configs()
    return _scheduler_instance


async def start_scheduler_service():
    """Start the scheduler as a service."""
    scheduler = await get_scheduler()
    await scheduler.start_scheduler()


def stop_scheduler_service():
    """Stop the scheduler service."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.stop_scheduler()