#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Buffered RichLog widget with timer-based flushing for performance.
Prevents GUI freezing during high-frequency log output by batching writes.
Includes emergency flush on errors and async-safe operations.
'''
from textual.widgets import RichLog
import time
import asyncio
from typing import Any, Optional


class RichLogExtended(RichLog):
    """
    Buffered RichLog with timer-based flushing and performance tracking.
    Accumulates log messages and flushes on buffer full, timer expiry, or emergency conditions.
    Thread-safe with async lock support.
    """
    def __init__(
            self,
            buffer_size: int = 10,
            flush_interval: float = 0.1,
            *args,
            **kwargs
    ):
        """
        Initialize buffered RichLog.
        
        Args:
            buffer_size: Number of messages to buffer before auto-flush
            flush_interval: Time in seconds between timer-based flushes
            *args, **kwargs: Passed to parent RichLog
        """
        super().__init__(*args, **kwargs)
        
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval
        self.buffer = []
        self.total_lines = 0
        self._last_flush = time.time()
        self._async_lock = asyncio.Lock()
        self.flush_count = 0
        self.total_flush_time = 0.0
        self.avg_flush_time = 0.0
        self.emergency_flush_count = 0
        self._flush_timer = None
    
    def write(
            self,
            content: Any,
            width: Optional[int] = None,
            expand: bool = False,
            shrink: bool = True,
            scroll_end: Optional[bool] = None,
            animate: bool = False
    ) -> 'RichLogExtended':
        """
        Buffer write with timer-based flushing.
        Flushes immediately on error messages or buffer full.
        
        Args:
            content: Content to write
            width: Optional width constraint
            expand: Whether to expand
            shrink: Whether to shrink
            scroll_end: Whether to scroll to end
            animate: Whether to animate
            
        Returns:
            Self for chaining
        """
        write_params = {
            'content': content,
            'width': width,
            'expand': expand,
            'shrink': shrink,
            'scroll_end': scroll_end,
            'animate': animate
        }
        
        self.buffer.append(write_params)
        
        content_str = str(content)
        if any(error_word in content_str.lower() for error_word in ['error', 'failed', 'exception', '❌']):
            self._flush_buffer()
            return self
        
        if len(self.buffer) > self.buffer_size * 2:
            self.emergency_flush_count += 1
            self._flush_buffer()
            return self
        
        if len(self.buffer) >= self.buffer_size:
            self._flush_buffer()
            return self
        
        self._start_flush_timer()
        
        return self
    
    def _start_flush_timer(self):
        """Start or restart flush timer."""
        if self._flush_timer and not self._flush_timer.done():
            self._flush_timer.cancel()
        
        self._flush_timer = asyncio.create_task(self._timer_flush())
    
    async def _timer_flush(self):
        """Flush after interval expires."""
        await asyncio.sleep(self.flush_interval)
        
        if self.buffer:
            self._flush_buffer()
    
    def _flush_buffer(self) -> None:
        """
        Flush all buffered writes to parent RichLog.
        Updates statistics and respects max_lines limit.
        """
        if not self.buffer:
            return
        
        if self._flush_timer and not self._flush_timer.done():
            self._flush_timer.cancel()
        
        flush_start = time.time()
        
        for write_params in self.buffer:
            super().write(**write_params)
            self.total_lines += 1
            
            if self.max_lines and self.total_lines > self.max_lines:
                super().clear()
                self.total_lines = 0
        
        flush_time = time.time() - flush_start
        self.flush_count += 1
        self.total_flush_time += flush_time
        self.avg_flush_time = self.total_flush_time / self.flush_count
        
        self.buffer.clear()
        self._last_flush = time.time()
    
    def clear(self) -> 'RichLogExtended':
        """Clear both display and buffer."""
        super().clear()
        self.buffer.clear()
        self.total_lines = 0
        return self
    
    def get_stats(self) -> dict:
        """
        Get buffering performance statistics.
        
        Returns:
            Dictionary with flush counts, times, and buffer state
        """
        return {
            'total_lines': self.total_lines,
            'buffer_size': len(self.buffer),
            'flush_count': self.flush_count,
            'avg_flush_time': self.avg_flush_time,
            'emergency_flush_count': self.emergency_flush_count,
            'buffer_efficiency': self.flush_count / max(1, self.total_lines) if self.total_lines > 0 else 0
        }
    
    def print_stats(self) -> 'RichLogExtended':
        """Print statistics to the log"""
        stats = self.get_stats()
        self.write(f"📊 RichLogExtended Stats:")
        self.write(f"   Total lines: {stats['total_lines']}")
        self.write(f"   Flush count: {stats['flush_count']}")
        self.write(f"   Avg flush time: {stats['avg_flush_time']:.3f}s")
        self.write(f"   Emergency flushes: {stats['emergency_flush_count']}")
        self.write(f"   Buffer efficiency: {stats['buffer_efficiency']:.2f}")
        self._flush_buffer()
        return self
