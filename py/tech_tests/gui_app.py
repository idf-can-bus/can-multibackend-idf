#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''

'''
import logging
import threading

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.widgets import Button, RichLog, Header, Footer, Select, Label

# set path to the parent directory
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rich_log_handler import RichLogHandler
from commands import ShellCommand, ShellCommandRunner

# Configure logging with custom handler
logger = logging.getLogger(__name__)
rich_log_handler = RichLogHandler()
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[rich_log_handler]
)


class RunnerTestGuiApp(App, ShellCommandRunner):
    """
    GUI application for running background tasks.
    Inherits from both App (Textual framework) and ShellCommandRunner.
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #table {
        grid-size: 4 2;
        grid-gutter: 0 1;  /* Vertical gap: 0, Horizontal gap: 1 */
        
        grid-rows: auto;
        height: auto;
    }

    #table Label {
        text-align: center;
        padding: 1;
    }

    #run {
        background: $success;
        color: white;
        width: 100%;
    }

    #status {
        width: 100%;
        height: 1fr;
        margin: 1 2;
        border: solid $primary;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+l", "clear_log", "Clear Log"),
    ]

    def __init__(self):
        # Initialize ShellCommandRunner first
        ShellCommandRunner.__init__(self)
        # Then initialize App
        App.__init__(self)

    def on_mount(self) -> None:
        """
        Called when the app is mounted.
        Sets up the RichLog widget for logging.
        """
        rich_log = self.query_one("#status")
        rich_log_handler.set_rich_log(rich_log)
        logger.info("App started")

    def compose(self) -> ComposeResult:
        yield Header('Runner of background tasks from GUI (proof of concept)')

        with Grid(id="table"):
            # First row - Headers
            yield Label("N times")
            yield Label("Sleep [s]")
            yield Label("Exit code")
            yield Label("")

            # Second row - Controls
            yield Select(
                [(str(n), n) for n in [5, 10, 50, 100, 1000]],
                id="n_times",
                value=5,
                prompt="N times",
                tooltip="Number of times to run the atomic task"

            )
            yield Select(
                [(str(n), n) for n in [0.2, 0.5, 0.8, 1.0, 2.0, 5.0]],
                id="sleep_s",
                value=0.2,
                prompt="Sleep [s]",
                tooltip="Time to sleep between atomic task executions"
            )
            yield Select(
                [(str(n), n) for n in [0, 1]],
                id="exit_code",
                value=0,
                prompt="Exit code",
                tooltip="Exit code for whole set of tasks (0 for success, 1 for failure)"
            )
            yield Button("Run", id="run")

        yield RichLog(highlight=True, id="status", name="testarea")
        yield Footer()

    def on_run(self, n_times: int, sleep_s: float, exit_code: int) -> None:
        """
        Handle the run button click event.
        Creates and starts a new thread to run the command.
        
        Args:
            n_times: Number of iterations
            sleep_s: Sleep time between iterations
            exit_code: Expected exit code
        """
        chain_of_commands= [
            ShellCommand(
                name="Background Task 1",
                command=f"python3 -u ./background_app.py -n {n_times} -t {sleep_s} -e {exit_code}",
                prompt='⚒️'
            ),ShellCommand(
                name="Background Task 2",
                command=f"python3 -u ./background_app.py -n {n_times} -t {sleep_s} -e 2",
                prompt='⚡'
            )
        ]



        # Run command in a separate thread to keep UI responsive
        thread = threading.Thread(
            target=self.run_commands,
            args=(chain_of_commands, logger)
        )
        thread.start()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events.
        Retrieves values from select boxes and starts the command.
        
        Args:
            event: Button press event
        """
        if event.button.id == "run":
            n_times = self.query_one("#n_times").value
            sleep_s = self.query_one("#sleep_s").value
            exit_code = self.query_one("#exit_code").value

            self.on_run(n_times, sleep_s, exit_code)

    def action_clear_log(self) -> None:
        """Clear the RichLog content"""
        try:
            rich_log = self.query_one(RichLog)
            rich_log.clear()
            logger.info("Log cleared")
        except Exception as e:
            logger.error(f"Failed to clear log: {e}")


def main():
    app = RunnerTestGuiApp()
    app.run()


if __name__ == "__main__":
    main()
