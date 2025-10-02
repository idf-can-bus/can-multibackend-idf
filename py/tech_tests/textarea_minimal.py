#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Minimal test for character-by-character writing to TextArea.
Tests if it's possible to write individual characters with time delays.
"""

import asyncio
import time
from textual.app import App, ComposeResult
from textual.widgets import TextArea, Button, Header, Footer


class TextAreaMinimalApp(App):
    """Minimal app to test character-by-character TextArea writing."""
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield TextArea(id="test-textarea", read_only=True)
        yield Button("Start Test", id="start-button")
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "start-button":
            event.button.disabled = True
            event.button.text = "Running..."
            self.run_worker(self.test_character_streaming())
    
    async def test_character_streaming(self) -> None:
        """Test writing characters one by one with delays."""
        textarea = self.query_one("#test-textarea", TextArea)
        
        # Test string to stream
        test_string = "[FAKE] ESP32 boot sequence started...\n"*100
        
        textarea.text = "=== Character-by-character streaming test ===\n"
        textarea.text += "Streaming: "
        
        # Write each character with delay
        for char in test_string:
            textarea.text += char
            await asyncio.sleep(0.01)  # 300ms delay between characters
        
        textarea.text += "\n=== Test completed ===\n"
        
        # Re-enable button
        button = self.query_one("#start-button", Button)
        button.disabled = False
        button.text = "Start Test"


if __name__ == "__main__":
    app = TextAreaMinimalApp()
    app.run()


