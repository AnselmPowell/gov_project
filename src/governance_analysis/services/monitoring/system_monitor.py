from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.traceback import install
from rich.theme import Theme
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict
import time
import asyncio
from contextlib import contextmanager
from contextlib import asynccontextmanager

# Install rich traceback handling
install(show_locals=True)

class ProcessStage:
    """Enumeration of processing stages"""
    UPLOAD = "Document Upload"
    PARSE = "Document Parsing"
    CHUNK = "Text Chunking"
    EXTRACT = "Best Practice Extraction"
    ANALYZE = "Theme Analysis"
    VECTORIZE = "Vector Storage"
    COMPLETE = "Process Complete"

class MonitoringTheme:
    """Custom color theme for monitoring"""
    CUSTOM_THEME = Theme({
        "info": "cyan",
        "success": "green",
        "warning": "yellow",
        "error": "red",
        "highlight": "magenta",
        "stage": "blue",
        "metric": "white"
    })

class ProcessMetrics:
    """Metrics tracking for process monitoring"""
    def __init__(self):
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.success = False
        self.error: Optional[str] = None
        self.stage_timings = {}
        self.document_metrics = defaultdict(dict)

    def complete(self, success: bool, error: Optional[str] = None):
        """Complete process tracking"""
        self.end_time = time.time()
        self.success = success
        self.error = error

    @property
    def duration(self) -> float:
        """Get total process duration"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def add_stage_timing(self, stage: str, duration: float):
        """Add timing for a stage"""
        self.stage_timings[stage] = duration

    def add_document_metric(self, doc_id: str, metric: str, value: Any):
        """Add metric for a document"""
        self.document_metrics[doc_id][metric] = value

class SystemMonitor:
    def __init__(self):
        print("\n[SystemMonitor] Initializing monitoring system")
        self.console = Console(theme=MonitoringTheme.CUSTOM_THEME)
        self.metrics = ProcessMetrics()
        self.current_stage = None
        self._progress = None
        print("[SystemMonitor] Monitor initialized")

    @contextmanager  # Changed from @asynccontextmanager
    def stage(self, stage_name: str):
        """Context manager for stage tracking"""
        print(f"\n[SystemMonitor.stage] Entering stage: {stage_name}")
        try:
            self.start_stage(stage_name)
            start_time = time.time()
            yield
            duration = time.time() - start_time
            self.complete_stage(stage_name, duration)
            print(f"[SystemMonitor.stage] Completed stage: {stage_name} in {duration:.2f}s")
        except Exception as e:
            print(f"[SystemMonitor.stage] Failed stage: {stage_name} with error: {str(e)}")
            self.fail_stage(stage_name, str(e))
            raise

    def start_stage(self, stage_name: str):
        """Start a new processing stage"""
        self.current_stage = stage_name
        self.console.print(Panel(
            f"[stage]Starting {stage_name}...",
            title="Stage Start",
            border_style="blue"
        ))

    def complete_stage(self, stage_name: str, duration: float):
        """Complete a processing stage"""
        self.metrics.add_stage_timing(stage_name, duration)
        self.console.print(Panel(
            f"""
            [success]✓ {stage_name} completed
            Duration: {duration:.2f}s
            """,
            title="Stage Complete",
            border_style="green"
        ))

    def fail_stage(self, stage_name: str, error: str):
        """Record stage failure"""
        self.console.print(Panel(
            f"""
            [error]✗ {stage_name} failed
            Error: {error}
            """,
            title="Stage Error",
            border_style="red"
        ))

    @asynccontextmanager
    async def document_progress(self, total_documents: int):
        """Track document processing progress"""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        )
        task_id = self._progress.add_task(
            f"[cyan]Processing: {total_documents} documents...",
            total=total_documents
        )
        
        try:
            self._progress.start()
            yield self._progress, task_id
        finally:
            self._progress.stop()

    def log_document_metric(self, doc_id: str, metric: str, value: Any):
        """Log metrics for a specific document"""
        self.metrics.add_document_metric(doc_id, metric, value)
        self.console.print(
            f"\n [metric]Document: {doc_id}: {metric} = {value} \n"
        )

    def display_summary(self):
        """Display processing summary"""
        if not self.metrics.end_time:
            self.metrics.complete(True)

        # Create summary table
        summary = Table(
            title="Processing Summary",
            show_header=True,
            header_style="bold magenta"
        )

        summary.add_column("Metric", style="cyan")
        summary.add_column("Value", style="yellow")

        # Add summary rows
        summary.add_row(
            "Total Duration",
            f"{self.metrics.duration:.2f}s"
        )
        summary.add_row(
            "Status",
            "[green]Success[/]" if self.metrics.success else "[red]Failed[/]"
        )
        if self.metrics.error:
            summary.add_row("Error", f"[red]{self.metrics.error}[/]")

        self.console.print(summary)

        # Display stage timings
        if self.metrics.stage_timings:
            timing_table = Table(
                title="Stage Timings",
                show_header=True,
                header_style="bold cyan"
            )
            
            timing_table.add_column("Stage")
            timing_table.add_column("Duration (s)")
            timing_table.add_column("Percentage")
            
            total_time = sum(self.metrics.stage_timings.values())
            for stage, duration in self.metrics.stage_timings.items():
                percentage = (duration / total_time) * 100
                timing_table.add_row(
                    stage,
                    f"{duration:.2f}",
                    f"{percentage:.1f}%"
                )
            
            self.console.print(timing_table)

        # Display document metrics
        if self.metrics.document_metrics:
            doc_table = Table(
                title="Document Metrics",
                show_header=True,
                header_style="bold blue"
            )
            
            doc_table.add_column("Document")
            doc_table.add_column("Metric")
            doc_table.add_column("Value")
            
            for doc_id, metrics in self.metrics.document_metrics.items():
                for metric, value in metrics.items():
                    doc_table.add_row(str(doc_id), metric, str(value))
            
            self.console.print(doc_table)