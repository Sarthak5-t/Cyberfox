from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System resource metrics."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    load_average: tuple[float, float, float]
    network_connections: int
    process_count: int


@dataclass
class ToolExecution:
    """Record of a tool execution."""
    tool_name: str
    command: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    success: Optional[bool] = None
    output_size: int = 0
    error: Optional[str] = None


class SystemMonitor:
    """Track system resources and tool execution performance."""

    def __init__(self):
        self._execution_history: list[ToolExecution] = []
        self._metrics_history: list[SystemMetrics] = []
        self._alerts: list[dict[str, Any]] = []
        self._thresholds: dict[str, float] = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
        }
        self._monitoring = False

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            import psutil

            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = os.getloadavg()
            network_connections = len(psutil.net_connections())
            process_count = len(psutil.pids())

            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_total_mb=memory.total / (1024 * 1024),
                disk_usage_percent=disk.percent,
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                load_average=load_avg,
                network_connections=network_connections,
                process_count=process_count,
            )

            self._metrics_history.append(metrics)
            self._check_thresholds(metrics)

            return metrics

        except ImportError:
            # Fallback if psutil not available
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0,
                memory_percent=0,
                memory_used_mb=0,
                memory_total_mb=0,
                disk_usage_percent=0,
                disk_free_gb=0,
                load_average=(0, 0, 0),
                network_connections=0,
                process_count=0,
            )

    def record_tool_execution(
        self,
        tool_name: str,
        command: str,
        start_time: float,
        end_time: float,
        success: bool,
        output_size: int = 0,
        error: Optional[str] = None,
    ) -> ToolExecution:
        """Record a tool execution."""
        execution = ToolExecution(
            tool_name=tool_name,
            command=command,
            start_time=start_time,
            end_time=end_time,
            duration=end_time - start_time,
            success=success,
            output_size=output_size,
            error=error,
        )

        self._execution_history.append(execution)
        logger.info(f"Tool execution recorded: {tool_name} ({execution.duration:.2f}s)")
        return execution

    def get_tool_performance(
        self,
        tool_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get tool performance statistics."""
        executions = self._execution_history
        if tool_name:
            executions = [e for e in executions if e.tool_name == tool_name]

        if not executions:
            return {"total_executions": 0}

        successful = [e for e in executions if e.success]
        failed = [e for e in executions if not e.success]
        durations = [e.duration for e in executions if e.duration is not None]

        return {
            "total_executions": len(executions),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(executions),
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "total_output_size": sum(e.output_size for e in executions),
        }

    def get_slowest_tools(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get the slowest tools by average execution time."""
        tool_stats: dict[str, list[float]] = {}

        for execution in self._execution_history:
            if execution.duration is not None:
                if execution.tool_name not in tool_stats:
                    tool_stats[execution.tool_name] = []
                tool_stats[execution.tool_name].append(execution.duration)

        tool_averages = []
        for tool_name, durations in tool_stats.items():
            avg_duration = sum(durations) / len(durations)
            tool_averages.append({
                "tool_name": tool_name,
                "avg_duration": avg_duration,
                "total_executions": len(durations),
            })

        tool_averages.sort(key=lambda x: x["avg_duration"], reverse=True)
        return tool_averages[:limit]

    def _check_thresholds(self, metrics: SystemMetrics) -> None:
        """Check metrics against thresholds and create alerts."""
        if metrics.cpu_percent > self._thresholds["cpu_percent"]:
            self._alerts.append({
                "type": "cpu_high",
                "value": metrics.cpu_percent,
                "threshold": self._thresholds["cpu_percent"],
                "timestamp": metrics.timestamp,
            })

        if metrics.memory_percent > self._thresholds["memory_percent"]:
            self._alerts.append({
                "type": "memory_high",
                "value": metrics.memory_percent,
                "threshold": self._thresholds["memory_percent"],
                "timestamp": metrics.timestamp,
            })

        if metrics.disk_usage_percent > self._thresholds["disk_usage_percent"]:
            self._alerts.append({
                "type": "disk_high",
                "value": metrics.disk_usage_percent,
                "threshold": self._thresholds["disk_usage_percent"],
                "timestamp": metrics.timestamp,
            })

    def get_alerts(
        self,
        alert_type: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get recent alerts."""
        alerts = self._alerts
        if alert_type:
            alerts = [a for a in alerts if a["type"] == alert_type]
        return alerts[-limit:]

    def clear_alerts(self) -> None:
        """Clear all alerts."""
        self._alerts.clear()

    def get_metrics_history(
        self,
        limit: int = 100,
    ) -> list[SystemMetrics]:
        """Get metrics history."""
        return self._metrics_history[-limit:]

    def get_statistics(self) -> dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "total_executions": len(self._execution_history),
            "metrics_recorded": len(self._metrics_history),
            "total_alerts": len(self._alerts),
            "thresholds": self._thresholds,
        }


# Global instance
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """Get the global system monitor instance."""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor
