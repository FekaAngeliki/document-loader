"""
Scheduler Management API Endpoints

Provides REST API endpoints for managing and monitoring the config-based scheduler.
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import sys
import os

# Add the parent directory to sys.path to import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.scheduling.config_scheduler import get_scheduler, ScheduleExecution
from .models import APIResponse, ErrorResponse, SchedulerStatus, ScheduleInfo, ExecutionInfo, ExecutionsResponse
from ..core.auth import get_current_user, RequireSchedulerRead, RequireSchedulerManage, RequireSchedulerTrigger, User
from ..core.audit import create_audit_event

router = APIRouter(prefix="/scheduler")

# Pydantic models for API requests
class TriggerRequest(BaseModel):
    """Request to trigger a manual sync."""
    config_name: str
    force: bool = Field(default=False, description="Force execution even if one is already running")

@router.get("/status", response_model=APIResponse[SchedulerStatus])
async def get_scheduler_status(
    current_user: User = RequireSchedulerRead
):
    """
    Get scheduler status and active schedules.
    
    Returns comprehensive information about the scheduler including:
    - Running status
    - Active schedule configurations
    - Pending and running executions
    - Next execution times for each schedule
    
    **Required Permission**: Any authenticated user
    """
    try:
        scheduler = await get_scheduler()
        status_info = scheduler.get_schedule_status()
        
        # Convert schedule info to API models
        schedules = {}
        for name, schedule_data in status_info['schedules'].items():
            schedules[name] = ScheduleInfo(
                config_name=name,
                enabled=schedule_data['enabled'],
                frequency=schedule_data['frequency'],
                time=schedule_data['time'],
                next_execution=schedule_data['next_execution']
            )
        
        status = SchedulerStatus(
            running=status_info['running'],
            active_schedules=status_info['active_schedules'],
            pending_executions=status_info['pending_executions'],
            running_executions=status_info['running_executions'],
            schedules=schedules,
            generated_at=datetime.utcnow()
        )
        
        await create_audit_event(
            user_id=current_user.username,
            action="scheduler.status.view",
            resource_type="scheduler",
            resource_id="system",
            details={"active_schedules": status_info['active_schedules']},
            ip_address="system"
        )
        
        return APIResponse(
            success=True,
            data=status,
            message="Scheduler status retrieved successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get scheduler status: {str(e)}"
        )

@router.get("/executions", response_model=APIResponse[ExecutionsResponse])
async def get_executions(
    config_name: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = 20,
    current_user: User = RequireSchedulerRead
):
    """
    Get recent scheduled executions with optional filtering.
    
    **Parameters**:
    - `config_name`: Filter by specific configuration name
    - `status_filter`: Filter by execution status (pending, running, completed, failed)
    - `limit`: Maximum number of executions to return (default: 20, max: 100)
    
    **Required Permission**: Any authenticated user
    """
    try:
        # Validate limit
        if limit > 100:
            limit = 100
        
        # Validate status filter
        valid_statuses = ['pending', 'running', 'completed', 'failed']
        if status_filter and status_filter not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status filter. Must be one of: {', '.join(valid_statuses)}"
            )
        
        scheduler = await get_scheduler()
        
        # Filter executions
        filtered_executions = []
        for exec_id, execution in scheduler.executions.items():
            if config_name and execution.config_name != config_name:
                continue
            if status_filter and execution.status != status_filter:
                continue
            filtered_executions.append(execution)
        
        # Sort by scheduled time (most recent first)
        filtered_executions.sort(key=lambda x: x.scheduled_time, reverse=True)
        total_count = len(filtered_executions)
        filtered_executions = filtered_executions[:limit]
        
        # Convert to API models
        executions = [
            ExecutionInfo(
                execution_id=exec.execution_id,
                config_name=exec.config_name,
                scheduled_time=exec.scheduled_time,
                status=exec.status,
                started_at=exec.started_at,
                completed_at=exec.completed_at,
                error_message=exec.error_message
            )
            for exec in filtered_executions
        ]
        
        response = ExecutionsResponse(
            executions=executions,
            total_count=total_count,
            filters={
                "config_name": config_name,
                "status": status_filter,
                "limit": limit
            },
            generated_at=datetime.utcnow()
        )
        
        await create_audit_event(
            user_id=current_user.username,
            action="scheduler.executions.view",
            resource_type="scheduler",
            resource_id="executions",
            details={
                "config_name": config_name,
                "status_filter": status_filter,
                "returned_count": len(executions),
                "total_count": total_count
            },
            ip_address="system"
        )
        
        return APIResponse(
            success=True,
            data=response,
            message=f"Retrieved {len(executions)} executions"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get executions: {str(e)}"
        )

@router.post("/trigger", response_model=APIResponse[Dict[str, str]])
async def trigger_sync(
    request: TriggerRequest,
    background_tasks: BackgroundTasks,
    current_user: User = RequireSchedulerTrigger
):
    """
    Manually trigger a scheduled sync for a configuration.
    
    **Parameters**:
    - `config_name`: Name of the configuration to sync
    - `force`: Force execution even if one is already running (default: false)
    
    **Required Permission**: Admin user
    """
    try:
        scheduler = await get_scheduler()
        
        # Check if config exists in scheduler
        if request.config_name not in scheduler.schedules:
            # Try to reload schedules first
            await scheduler.load_schedules_from_configs()
            
            if request.config_name not in scheduler.schedules:
                available_configs = list(scheduler.schedules.keys())
                raise HTTPException(
                    status_code=404,
                    detail=f"Configuration '{request.config_name}' not found in active schedules. Available: {available_configs}"
                )
        
        # Check if already running (unless forced)
        if not request.force:
            for execution in scheduler.executions.values():
                if execution.config_name == request.config_name and execution.status == "running":
                    raise HTTPException(
                        status_code=409,
                        detail=f"Sync already running for '{request.config_name}'. Use force=true to override."
                    )
        
        # Create manual execution
        schedule = scheduler.schedules[request.config_name]
        current_time = datetime.now()
        
        await scheduler._schedule_execution(request.config_name, schedule, current_time)
        
        await create_audit_event(
            user_id=current_user.username,
            action="scheduler.trigger",
            resource_type="scheduler",
            resource_id=request.config_name,
            details={
                "config_name": request.config_name,
                "forced": request.force
            },
            ip_address="system"
        )
        
        return APIResponse(
            success=True,
            data={
                "config_name": request.config_name,
                "status": "triggered",
                "message": f"Manual sync triggered for '{request.config_name}'"
            },
            message="Sync triggered successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger sync: {str(e)}"
        )

@router.post("/reload", response_model=APIResponse[Dict[str, int]])
async def reload_configurations(
    current_user: User = RequireSchedulerManage
):
    """
    Reload scheduler configurations from the database.
    
    Forces the scheduler to re-read all configuration files and update
    its internal schedule definitions. Useful after adding or modifying
    configuration files.
    
    **Required Permission**: Admin user
    """
    try:
        scheduler = await get_scheduler()
        old_count = len(scheduler.schedules)
        
        await scheduler.load_schedules_from_configs()
        new_count = len(scheduler.schedules)
        
        await create_audit_event(
            user_id=current_user.username,
            action="scheduler.reload",
            resource_type="scheduler",
            resource_id="configurations",
            details={
                "previous_count": old_count,
                "current_count": new_count,
                "change": new_count - old_count
            },
            ip_address="system"
        )
        
        return APIResponse(
            success=True,
            data={
                "previous_count": old_count,
                "current_count": new_count,
                "change": new_count - old_count
            },
            message=f"Configurations reloaded. {new_count} active schedules."
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reload configurations: {str(e)}"
        )

@router.get("/schedule/{config_name}", response_model=APIResponse[ScheduleInfo])
async def get_schedule_info(
    config_name: str,
    current_user: User = RequireSchedulerRead
):
    """
    Get detailed schedule information for a specific configuration.
    
    **Parameters**:
    - `config_name`: Name of the configuration to get schedule info for
    
    **Required Permission**: Any authenticated user
    """
    try:
        scheduler = await get_scheduler()
        
        if config_name not in scheduler.schedules:
            await scheduler.load_schedules_from_configs()
            
            if config_name not in scheduler.schedules:
                available_configs = list(scheduler.schedules.keys())
                raise HTTPException(
                    status_code=404,
                    detail=f"Configuration '{config_name}' not found in schedules. Available: {available_configs}"
                )
        
        schedule_config = scheduler.schedules[config_name]
        next_execution = scheduler._calculate_next_execution(schedule_config)
        
        schedule_info = ScheduleInfo(
            config_name=schedule_config.config_name,
            enabled=schedule_config.enabled,
            frequency=schedule_config.frequency,
            time=schedule_config.time,
            cron_expression=schedule_config.cron_expression,
            timezone=schedule_config.timezone,
            max_duration_hours=schedule_config.max_duration_hours,
            retry_attempts=schedule_config.retry_attempts,
            notification_emails=schedule_config.notification_emails,
            next_execution=next_execution
        )
        
        await create_audit_event(
            user_id=current_user.username,
            action="scheduler.schedule.view",
            resource_type="scheduler",
            resource_id=config_name,
            details={"config_name": config_name},
            ip_address="system"
        )
        
        return APIResponse(
            success=True,
            data=schedule_info,
            message=f"Schedule information for '{config_name}'"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get schedule info: {str(e)}"
        )