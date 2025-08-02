#!/usr/bin/env python3
"""
Monitoring and metrics collection for scrapers
"""

import time
import logging
from typing import Dict, Optional, Callable, Any
from contextlib import contextmanager
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field
import json


@dataclass
class ScraperMetrics:
    """Container for scraper metrics"""
    name: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # Counters
    urls_fetched: int = 0
    spots_found: int = 0
    spots_saved: int = 0
    errors: int = 0
    rate_limits: int = 0
    
    # Timing
    fetch_times: list = field(default_factory=list)
    save_times: list = field(default_factory=list)
    
    # Data quality
    spots_with_coordinates: int = 0
    spots_hidden: int = 0
    validation_failures: int = 0
    
    # Resource usage
    memory_usage_mb: Optional[float] = None
    
    def add_fetch_time(self, duration: float):
        """Add fetch duration"""
        self.fetch_times.append(duration)
        
    def add_save_time(self, duration: float):
        """Add save duration"""
        self.save_times.append(duration)
        
    def avg_fetch_time(self) -> float:
        """Calculate average fetch time"""
        return sum(self.fetch_times) / len(self.fetch_times) if self.fetch_times else 0
        
    def avg_save_time(self) -> float:
        """Calculate average save time"""
        return sum(self.save_times) / len(self.save_times) if self.save_times else 0
        
    def total_duration(self) -> float:
        """Get total duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time
        
    def success_rate(self) -> float:
        """Calculate success rate"""
        total = self.spots_found
        if total == 0:
            return 0.0
        return (self.spots_saved / total) * 100
        
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging"""
        return {
            "name": self.name,
            "duration": self.total_duration(),
            "urls_fetched": self.urls_fetched,
            "spots_found": self.spots_found,
            "spots_saved": self.spots_saved,
            "errors": self.errors,
            "rate_limits": self.rate_limits,
            "spots_with_coordinates": self.spots_with_coordinates,
            "spots_hidden": self.spots_hidden,
            "validation_failures": self.validation_failures,
            "success_rate": self.success_rate(),
            "avg_fetch_time": self.avg_fetch_time(),
            "avg_save_time": self.avg_save_time(),
            "memory_usage_mb": self.memory_usage_mb
        }


class MetricsCollector:
    """Collect and manage scraper metrics"""
    
    def __init__(self):
        self.metrics: Dict[str, ScraperMetrics] = {}
        self.logger = logging.getLogger(__name__)
        
    def start_scraper(self, scraper_name: str) -> ScraperMetrics:
        """Start tracking a scraper"""
        metrics = ScraperMetrics(name=scraper_name)
        self.metrics[scraper_name] = metrics
        self.logger.info(f"Started tracking {scraper_name}")
        return metrics
        
    def end_scraper(self, scraper_name: str):
        """End tracking a scraper"""
        if scraper_name in self.metrics:
            self.metrics[scraper_name].end_time = time.time()
            self._log_metrics(self.metrics[scraper_name])
            
    def get_metrics(self, scraper_name: str) -> Optional[ScraperMetrics]:
        """Get metrics for a scraper"""
        return self.metrics.get(scraper_name)
        
    def _log_metrics(self, metrics: ScraperMetrics):
        """Log scraper metrics"""
        self.logger.info(
            f"Scraper '{metrics.name}' completed",
            extra={"metrics": metrics.to_dict()}
        )
        
    def get_summary(self) -> Dict:
        """Get summary of all scrapers"""
        return {
            name: metrics.to_dict()
            for name, metrics in self.metrics.items()
        }
        
    def save_metrics(self, filepath: str = "logs/metrics.json"):
        """Save metrics to file"""
        with open(filepath, 'w') as f:
            json.dump(self.get_summary(), f, indent=2)


# Global metrics collector
_metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector"""
    return _metrics_collector


@contextmanager
def track_operation(operation: str, metrics: ScraperMetrics):
    """Context manager for tracking operation timing"""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        if operation == "fetch":
            metrics.add_fetch_time(duration)
        elif operation == "save":
            metrics.add_save_time(duration)


def log_memory_usage(metrics: ScraperMetrics):
    """Log current memory usage"""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        metrics.memory_usage_mb = memory_mb
    except ImportError:
        pass  # psutil not installed


class PerformanceMonitor:
    """Monitor performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.thresholds = {
            "fetch_time": 5.0,  # seconds
            "save_time": 1.0,   # seconds
            "error_rate": 0.1,  # 10%
            "memory_mb": 500    # MB
        }
        
    def check_performance(self, metrics: ScraperMetrics):
        """Check if performance is within thresholds"""
        warnings = []
        
        # Check fetch time
        avg_fetch = metrics.avg_fetch_time()
        if avg_fetch > self.thresholds["fetch_time"]:
            warnings.append(f"Slow fetch time: {avg_fetch:.2f}s")
            
        # Check save time
        avg_save = metrics.avg_save_time()
        if avg_save > self.thresholds["save_time"]:
            warnings.append(f"Slow save time: {avg_save:.2f}s")
            
        # Check error rate
        if metrics.urls_fetched > 0:
            error_rate = metrics.errors / metrics.urls_fetched
            if error_rate > self.thresholds["error_rate"]:
                warnings.append(f"High error rate: {error_rate:.1%}")
                
        # Check memory usage
        if metrics.memory_usage_mb:
            if metrics.memory_usage_mb > self.thresholds["memory_mb"]:
                warnings.append(f"High memory usage: {metrics.memory_usage_mb:.1f}MB")
                
        # Log warnings
        for warning in warnings:
            self.logger.warning(f"{metrics.name}: {warning}")
            
        return warnings


class AlertManager:
    """Manage alerts for critical issues"""
    
    def __init__(self, alert_handlers: Optional[Dict[str, Callable]] = None):
        self.logger = logging.getLogger(__name__)
        self.handlers = alert_handlers or {}
        self.alerts_sent = defaultdict(list)
        
    def add_handler(self, name: str, handler: Callable[[str, Any], None]):
        """Add an alert handler"""
        self.handlers[name] = handler
        
    def send_alert(self, severity: str, message: str, context: Optional[Dict] = None):
        """Send an alert"""
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "message": message,
            "context": context or {}
        }
        
        # Log the alert
        self.logger.error(f"ALERT [{severity}]: {message}", extra=alert_data)
        
        # Send to handlers
        for name, handler in self.handlers.items():
            try:
                handler(severity, alert_data)
                self.alerts_sent[name].append(alert_data)
            except Exception as e:
                self.logger.error(f"Alert handler '{name}' failed: {e}")
                
    def check_metrics_alerts(self, metrics: ScraperMetrics):
        """Check metrics and send alerts if needed"""
        # Critical error rate
        if metrics.urls_fetched > 10:
            error_rate = metrics.errors / metrics.urls_fetched
            if error_rate > 0.5:  # 50% errors
                self.send_alert(
                    "CRITICAL",
                    f"Scraper '{metrics.name}' has {error_rate:.0%} error rate",
                    {"metrics": metrics.to_dict()}
                )
                
        # No data found
        if metrics.urls_fetched > 0 and metrics.spots_found == 0:
            self.send_alert(
                "WARNING",
                f"Scraper '{metrics.name}' found no spots after {metrics.urls_fetched} URLs",
                {"metrics": metrics.to_dict()}
            )


# Example alert handlers
def console_alert_handler(severity: str, alert_data: Dict):
    """Print alerts to console"""
    print(f"\n🚨 ALERT [{severity}]: {alert_data['message']}\n")


def file_alert_handler(severity: str, alert_data: Dict):
    """Write alerts to file"""
    with open("logs/alerts.log", "a") as f:
        f.write(json.dumps(alert_data) + "\n")


# Initialize global alert manager
_alert_manager = AlertManager({
    "console": console_alert_handler,
    "file": file_alert_handler
})


def get_alert_manager() -> AlertManager:
    """Get global alert manager"""
    return _alert_manager