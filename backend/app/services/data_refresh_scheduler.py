"""
Data Refresh Scheduler Service

This module handles scheduled data refresh operations including:
- Provider directory scraping
- Structured data updates
- Cache invalidation
- Error handling and retry logic
"""

import logging
import asyncio
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from .provider_scraper import ProviderDirectoryScraper
from .structured_data_service import StructuredDataService
from .vector_db_service import update_provider_data, get_provider_statistics

logger = logging.getLogger(__name__)

class RefreshFrequency(Enum):
    """Frequency options for data refresh"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    MANUAL = "manual"

@dataclass
class RefreshJob:
    """Configuration for a data refresh job"""
    name: str
    frequency: RefreshFrequency
    function: Callable
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    error_count: int = 0
    max_retries: int = 3
    enabled: bool = True

class DataRefreshScheduler:
    """Service for scheduling and managing data refresh operations"""
    
    def __init__(self):
        self.jobs: Dict[str, RefreshJob] = {}
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.provider_scraper = ProviderDirectoryScraper()
        self.structured_data_service = StructuredDataService()
        
        # Initialize default jobs
        self._initialize_default_jobs()
    
    def _initialize_default_jobs(self) -> None:
        """Initialize default refresh jobs"""
        
        # Monthly provider count refresh
        self.add_job(
            name="provider_count_refresh",
            frequency=RefreshFrequency.MONTHLY,
            function=self._refresh_provider_data,
            enabled=True
        )
        
        # Weekly data validation
        self.add_job(
            name="data_validation",
            frequency=RefreshFrequency.WEEKLY,
            function=self._validate_data_freshness,
            enabled=True
        )
        
        # Daily cache cleanup
        self.add_job(
            name="cache_cleanup",
            frequency=RefreshFrequency.DAILY,
            function=self._cleanup_cache,
            enabled=True
        )
    
    def add_job(
        self, 
        name: str, 
        frequency: RefreshFrequency, 
        function: Callable,
        enabled: bool = True,
        max_retries: int = 3
    ) -> None:
        """Add a new refresh job"""
        job = RefreshJob(
            name=name,
            frequency=frequency,
            function=function,
            enabled=enabled,
            max_retries=max_retries
        )
        
        # Calculate next run time
        job.next_run = self._calculate_next_run(frequency)
        
        self.jobs[name] = job
        logger.info(f"Added refresh job: {name} (frequency: {frequency.value})")
    
    def _calculate_next_run(self, frequency: RefreshFrequency) -> datetime:
        """Calculate next run time based on frequency"""
        now = datetime.now()
        
        if frequency == RefreshFrequency.DAILY:
            # Run at 2 AM daily
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        elif frequency == RefreshFrequency.WEEKLY:
            # Run on Sundays at 3 AM
            days_ahead = 6 - now.weekday()  # Sunday is 6
            if days_ahead <= 0:  # Today is Sunday
                days_ahead += 7
            next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
            next_run += timedelta(days=days_ahead)
            
        elif frequency == RefreshFrequency.MONTHLY:
            # Run on the 1st of each month at 4 AM
            if now.day == 1 and now.hour < 4:
                next_run = now.replace(day=1, hour=4, minute=0, second=0, microsecond=0)
            else:
                # Next month
                if now.month == 12:
                    next_run = now.replace(year=now.year + 1, month=1, day=1, 
                                         hour=4, minute=0, second=0, microsecond=0)
                else:
                    next_run = now.replace(month=now.month + 1, day=1, 
                                         hour=4, minute=0, second=0, microsecond=0)
        else:
            # Manual jobs don't have automatic scheduling
            next_run = None
        
        return next_run
    
    def start_scheduler(self) -> None:
        """Start the background scheduler thread"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        logger.info("Data refresh scheduler started")
    
    def stop_scheduler(self) -> None:
        """Stop the background scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Data refresh scheduler stopped")
    
    def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Check each job
                for job_name, job in self.jobs.items():
                    if not job.enabled or job.next_run is None:
                        continue
                    
                    if current_time >= job.next_run:
                        logger.info(f"Running scheduled job: {job_name}")
                        self._execute_job(job)
                
                # Sleep for 1 minute before checking again
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Continue after error
    
    def _execute_job(self, job: RefreshJob) -> None:
        """Execute a refresh job with error handling"""
        try:
            job.last_run = datetime.now()
            
            # Execute the job function
            result = job.function()
            
            # Mark as successful
            job.last_success = datetime.now()
            job.error_count = 0
            
            # Schedule next run
            job.next_run = self._calculate_next_run(job.frequency)
            
            logger.info(f"Job {job.name} completed successfully")
            
        except Exception as e:
            job.error_count += 1
            logger.error(f"Job {job.name} failed (attempt {job.error_count}): {e}")
            
            if job.error_count >= job.max_retries:
                logger.error(f"Job {job.name} disabled after {job.max_retries} failures")
                job.enabled = False
            else:
                # Retry in 1 hour
                job.next_run = datetime.now() + timedelta(hours=1)
                logger.info(f"Job {job.name} will retry at {job.next_run}")
    
    def _refresh_provider_data(self) -> Dict[str, Any]:
        """Refresh provider count data from DHS directory"""
        logger.info("Starting provider data refresh...")
        
        try:
            # Scrape current provider data
            total_count, county_counts, providers = self.provider_scraper.scrape_provider_data()
            
            if total_count > 0:
                # Update structured data
                source_url = "https://www.dhs.state.mn.us/main/idcplg?IdcService=GET_DYNAMIC_CONVERSION&RevisionSelectionMethod=LatestReleased&dDocName=dhs16_155949"
                
                success = update_provider_data(
                    total_count=total_count,
                    by_county=county_counts,
                    source="Minnesota DHS Provider Directory",
                    source_url=source_url
                )
                
                if success:
                    logger.info(f"Provider data updated: {total_count} total providers")
                    
                    # Export detailed provider data if available
                    if providers:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        export_file = f"data/provider_export_{timestamp}.json"
                        self.provider_scraper.export_provider_data(providers, export_file)
                    
                    return {
                        "status": "success",
                        "total_providers": total_count,
                        "counties": len(county_counts),
                        "detailed_providers": len(providers)
                    }
                else:
                    raise Exception("Failed to update provider data in structured storage")
            else:
                logger.warning("No provider data found during scraping")
                return {"status": "warning", "message": "No provider data found"}
                
        except Exception as e:
            logger.error(f"Provider data refresh failed: {e}")
            raise
    
    def _validate_data_freshness(self) -> Dict[str, Any]:
        """Validate that data is fresh and identify stale entries"""
        logger.info("Validating data freshness...")
        
        try:
            # Check structured data freshness
            stale_entries = self.structured_data_service.get_stale_entries(max_age_days=60)
            
            # Check provider data age
            provider_stats = get_provider_statistics()
            provider_age_days = None
            
            if provider_stats.get('total_providers_last_updated'):
                last_updated = datetime.fromisoformat(provider_stats['total_providers_last_updated'])
                provider_age_days = (datetime.now() - last_updated).days
            
            validation_results = {
                "status": "success",
                "stale_entries": len(stale_entries),
                "provider_data_age_days": provider_age_days,
                "recommendations": []
            }
            
            # Add recommendations based on findings
            if len(stale_entries) > 5:
                validation_results["recommendations"].append("Consider refreshing structured data")
            
            if provider_age_days and provider_age_days > 45:
                validation_results["recommendations"].append("Provider data is getting stale, consider manual refresh")
            
            logger.info(f"Data validation complete: {len(stale_entries)} stale entries found")
            return validation_results
            
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            raise
    
    def _cleanup_cache(self) -> Dict[str, Any]:
        """Clean up cached data and temporary files"""
        logger.info("Performing cache cleanup...")
        
        try:
            # Clear vector database cache to force reload of fresh data
            import backend.app.services.vector_db_service as vector_db
            vector_db._cached_data = None
            
            # Clean up old export files (keep last 10)
            import os
            import glob
            
            export_pattern = "data/provider_export_*.json"
            export_files = glob.glob(export_pattern)
            export_files.sort(key=os.path.getmtime, reverse=True)
            
            cleaned_files = 0
            for old_file in export_files[10:]:  # Keep only the 10 most recent
                try:
                    os.remove(old_file)
                    cleaned_files += 1
                except OSError:
                    pass
            
            logger.info(f"Cache cleanup complete: cleared vector cache, removed {cleaned_files} old files")
            return {"status": "success", "files_cleaned": cleaned_files}
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            raise
    
    def run_job_manually(self, job_name: str) -> Dict[str, Any]:
        """Manually run a specific job"""
        if job_name not in self.jobs:
            raise ValueError(f"Job {job_name} not found")
        
        job = self.jobs[job_name]
        logger.info(f"Manually running job: {job_name}")
        
        try:
            result = job.function()
            job.last_success = datetime.now()
            job.error_count = 0
            
            return {
                "status": "success",
                "job": job_name,
                "result": result,
                "executed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            job.error_count += 1
            logger.error(f"Manual job execution failed: {e}")
            raise
    
    def get_job_status(self) -> Dict[str, Any]:
        """Get status of all scheduled jobs"""
        status = {
            "scheduler_running": self.running,
            "jobs": {}
        }
        
        for job_name, job in self.jobs.items():
            status["jobs"][job_name] = {
                "enabled": job.enabled,
                "frequency": job.frequency.value,
                "next_run": job.next_run.isoformat() if job.next_run else None,
                "last_run": job.last_run.isoformat() if job.last_run else None,
                "last_success": job.last_success.isoformat() if job.last_success else None,
                "error_count": job.error_count,
                "max_retries": job.max_retries
            }
        
        return status
    
    def enable_job(self, job_name: str) -> None:
        """Enable a specific job"""
        if job_name in self.jobs:
            self.jobs[job_name].enabled = True
            self.jobs[job_name].error_count = 0
            self.jobs[job_name].next_run = self._calculate_next_run(self.jobs[job_name].frequency)
            logger.info(f"Enabled job: {job_name}")
        else:
            raise ValueError(f"Job {job_name} not found")
    
    def disable_job(self, job_name: str) -> None:
        """Disable a specific job"""
        if job_name in self.jobs:
            self.jobs[job_name].enabled = False
            logger.info(f"Disabled job: {job_name}")
        else:
            raise ValueError(f"Job {job_name} not found")

# Global scheduler instance
data_refresh_scheduler = DataRefreshScheduler() 