# minimal_tabs_encapsulated_with_button.py
#!/usr/bin/env python
# -*- coding: utf-8 -*-
from textual.app import App, ComposeResult
from textual.widgets import Footer, TabbedContent, TabPane, Static, RichLog, Button
from textual.containers import Vertical, Container


class OverviewPanel(Vertical):
    """Simple panel with static text content."""
    def compose(self) -> ComposeResult:
        yield Static("Overview", id="ov-title")
        yield Static("This is a demo of encapsulating each tab into its own widget.")
        yield Static("No behavior here—layout only.")


class LogsPanel(Container):
    """Panel with RichLog and a button to append messages."""
    def compose(self) -> ComposeResult:
        # RichLog and a button stacked vertically
        yield RichLog(id="log")
        yield Button("Add line", id="add-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Append a line to the RichLog when the button is pressed."""
        # Find our RichLog by ID and write a message
        log: RichLog = self.query_one("#log", RichLog)
        log.write("Button pressed – new log entry")


class DemoApp(App):
    """App composed from encapsulated tab widgets."""
    CSS = '''
        #log {
            height: 1fr;          /* RichLog roztáhnout na zbytek výšky */
            border: heavy $primary;
        }

        #add-btn {
            margin-top: 1;
            width: 20;
            align: center middle;
        }
'''

    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("Overview"):
                yield OverviewPanel()
            with TabPane("Logs"):
                yield LogsPanel()
        yield Footer()


if __name__ == "__main__":
    DemoApp().run()
