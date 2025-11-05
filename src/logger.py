"""
Logger module - Structured and colored logs with Rich.
"""

import logging
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn


class StripeLogger:
    """Logger configured with Rich for elegant logs."""

    def __init__(self, level: str = "INFO") -> None:
        """
        Initialize the logger.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        self.console = Console()

        # Logger configuration
        logging.basicConfig(
            level=level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True)]
        )

        self.logger = logging.getLogger("stripe_copier")

    def info(self, message: str, **kwargs: object) -> None:
        """Log an info message."""
        self.logger.info(message, extra=kwargs)

    def debug(self, message: str, **kwargs: object) -> None:
        """Log a debug message."""
        self.logger.debug(message, extra=kwargs)

    def warning(self, message: str, **kwargs: object) -> None:
        """Log a warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs: object) -> None:
        """Log an error message."""
        self.logger.error(message, extra=kwargs)

    def success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[green]✓[/green] {message}")

    def section(self, title: str) -> None:
        """Display a section title."""
        self.console.rule(f"[bold blue]{title}[/bold blue]")

    def print(self, message: str, style: Optional[str] = None) -> None:
        """Display a message with optional style."""
        if style:
            self.console.print(message, style=style)
        else:
            self.console.print(message)

    def table(self, title: str, data: dict[str, str | int]) -> None:
        """Display data as a table."""
        from rich.table import Table

        table = Table(title=title, show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for key, value in data.items():
            table.add_row(key, str(value))

        self.console.print(table)

    def create_progress(self) -> Progress:
        """Create a progress bar."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )

    def confirm(self, message: str) -> bool:
        """
        Ask user for confirmation.

        Args:
            message: Confirmation message

        Returns:
            True if user confirms, False otherwise
        """
        from rich.prompt import Confirm
        return Confirm.ask(message)


# Global logger instance (singleton pattern)
_logger_instance: Optional[StripeLogger] = None


def get_logger(level: str = "INFO") -> StripeLogger:
    """
    Get the logger instance (singleton).

    Args:
        level: Log level (only used on first initialization)

    Returns:
        StripeLogger instance
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StripeLogger(level=level)
    return _logger_instance
