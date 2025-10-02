#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minimal test for character-by-character writing to RichLog.
Tests if it's possible to write individual characters with time delays.
"""

import asyncio
import time
from textual.app import App, ComposeResult
from textual.widgets import RichLog, Button, Header, Footer


class RichLogMinimalApp(App):
    """Minimal app to test character-by-character RichLog writing."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="test-log")
        yield Button("Start Test", id="start-button")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-button":
            event.button.disabled = True
            event.button.text = "Running..."
            self.run_worker(self.test_character_streaming())
    
    async def test_character_streaming(self) -> None:
        """Test writing characters one by one with delays."""
        log = self.query_one("#test-log", RichLog)
        
        # Test string to stream
        test_string = "[FAKE] ESP32 boot sequence started...\n"
        
        log.write("=== Character-by-character streaming test ===\n")
        log.write("Streaming: ")
        
        # Write each character with delay
        for char in test_string:
            log.write(char)
            await asyncio.sleep(0.3)  # 300ms delay between characters
        
        log.write("\n=== Test completed ===\n")
        
        # Re-enable button
        button = self.query_one("#start-button", Button)
        button.disabled = False
        button.text = "Start Test"


if __name__ == "__main__":
    app = RichLogMinimalApp()
    app.run()
