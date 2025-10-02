from textual.app import App, ComposeResult
from textual.widgets import TabbedContent, TabPane, Static, Footer

class TestApp(App):
    def compose(self) -> ComposeResult:
        with TabbedContent():
            with TabPane("First Tab"):
                yield Static("Content of the first tab")
            with TabPane("Second Tab"):
                yield Static("Content of the second tab")
        yield Footer()

if __name__ == "__main__":
    app = TestApp()
    app.run()
