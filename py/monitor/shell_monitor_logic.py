#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Shell-based monitor logic using ShellCommandProcess.
Manages monitor processes for each port with serial port streaming.
Supports both real serial ports and fake monitoring for testing.
'''

import os
import asyncio
from typing import Dict
from py.shell_commands import ShellCommandConfig


class PortMonitorProcess:
    """
    Asynchronous subprocess wrapper for serial port monitoring.
    Streams subprocess output directly to log widget character-by-character or buffered.
    Bypasses standard logging for real-time output display without GUI blocking.
    """
    
    def __init__(
            self,
            config: ShellCommandConfig,
            port_log_widget,
            read_timeout: float = 0.001,
            chunk_size: int = 4096,
            flush_interval: float = 0.05
    ):
        """
        Initialize monitor process.
        
        Args:
            config: Shell command configuration with monitor command
            port_log_widget: Log widget to write output to
            read_timeout: Timeout for subprocess read operations (seconds)
            chunk_size: Bytes to read per operation (larger = faster)
            flush_interval: Minimum interval between writes to widget (seconds)
        """
        self.config = config
        self.port_log_widget = port_log_widget
        self.process = None
        self.running = False
        self.read_timeout = read_timeout
        self.chunk_size = chunk_size
        self.flush_interval = flush_interval
        self.stdout_buffer = ""
        self.stderr_buffer = ""
        self.stdout_task = None
        self.stderr_task = None
        self.last_flush_time = 0.0
        
    async def start(self) -> int:
        """
        Start subprocess and begin streaming output to log widget.
        
        Returns:
            Process return code
        """
        try:
            self.process = await asyncio.create_subprocess_shell(
                self.config.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.running = True
            
            self.stdout_task = asyncio.create_task(self._stream_output(self.process.stdout, prefix=""))
            self.stderr_task = asyncio.create_task(self._stream_output(self.process.stderr, prefix="STDERR: "))
            await self.process.wait()
            await asyncio.gather(self.stdout_task, self.stderr_task, return_exceptions=True)
            
            return self.process.returncode
            
        except Exception as e:
            self._write_to_textarea(f"Process failed: {e}\n")
            return -1
            
    async def _stream_output(self, stream, prefix: str = ""):
        """
        Stream subprocess output to log widget with optimized buffering.
        Reads larger chunks and flushes periodically for better performance.
        
        Args:
            stream: Asyncio stream to read from (stdout or stderr)
            prefix: Prefix string for output lines (e.g., "STDERR: ")
        """
        try:
            buffer = ""
            last_flush = asyncio.get_event_loop().time()
            
            while self.running:
                try:
                    data = await asyncio.wait_for(
                        stream.read(self.chunk_size), 
                        timeout=self.read_timeout
                    )
                    if not data:
                        break
                    
                    chunk = data.decode('utf-8', errors='replace')
                    buffer += chunk
                    
                    current_time = asyncio.get_event_loop().time()
                    time_since_flush = current_time - last_flush
                    
                    should_flush = (
                        '\n' in chunk or
                        len(buffer) >= self.chunk_size or
                        time_since_flush >= self.flush_interval
                    )
                    
                    if should_flush and buffer:
                        self._write_to_textarea(f"{prefix}{buffer}")
                        buffer = ""
                        last_flush = current_time
                        
                except asyncio.TimeoutError:
                    if buffer:
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_flush >= self.flush_interval:
                            self._write_to_textarea(f"{prefix}{buffer}")
                            buffer = ""
                            last_flush = current_time
                    continue
                except Exception as e:
                    self._write_to_textarea(f"Stream error: {e}\n")
                    break
                    
            if buffer:
                self._write_to_textarea(f"{prefix}{buffer}")
                    
        except Exception as e:
            self._write_to_textarea(f"Stream error: {e}\n")
    
    def _write_to_textarea(self, text: str) -> None:
        """
        Write text to log widget.
        Removes carriage return characters for clean output.
        
        Args:
            text: Text to write to widget
        """
        text = text.replace('\r', '')
        try:
            self.port_log_widget.write(text)
        except Exception as e:
            print(f"Error writing to widget: {e}")
    
    async def run_end_wait(self) -> bool:
        """
        Start process and wait for completion.
        
        Returns:
            True if process completed successfully (return code 0)
        """
        return_code = await self.start()
        return return_code == 0
        
    async def terminate(self) -> None:
        """
        Terminate running subprocess gracefully.
        Tries SIGTERM first, then SIGKILL if needed.
        Waits for stream tasks to complete.
        """
        if self.process and self.running:
            self.running = False
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=1.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
                if self.stdout_task:
                    await asyncio.wait_for(self.stdout_task, timeout=0.5)
                if self.stderr_task:
                    await asyncio.wait_for(self.stderr_task, timeout=0.5)
                    
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                print(f"Error terminating process: {e}")


class ShellMonitorLogic:
    """
    Manager for multiple serial port monitor processes.
    Handles starting, stopping, and tracking monitor subprocesses.
    Supports both real serial ports (/dev/ttyACM*, /dev/ttyUSB*) and fake ports for testing.
    """
    BAUD_RATE = 115200
    PORT_PARAMS = 'raw -echo -ixon -ixoff -crtscts'

    
    def __init__(
        self, 
        idf_setup_path: str = "~/esp/v5.4.1/esp-idf/export.sh",
        read_timeout: float = 0.001,
        chunk_size: int = 4096,
        flush_interval: float = 0.05
    ):
        """
        Initialize monitor logic manager.
        
        Args:
            idf_setup_path: Path to ESP-IDF environment setup script
            read_timeout: Subprocess read timeout in seconds
            chunk_size: Bytes to read per operation (larger = faster throughput)
            flush_interval: Minimum interval between writes to widget (seconds)
        """
        self.idf_setup_path = os.path.expanduser(idf_setup_path)
        self.read_timeout = read_timeout
        self.chunk_size = chunk_size
        self.flush_interval = flush_interval
        self.active_monitors: Dict[str, PortMonitorProcess] = {}
        self.port_loggers: Dict[str, object] = {}
        self.worker_tasks: Dict[str, object] = {}
    
    def start_monitor_for_gui(self, port: str, monitor_log_widget, gui_run_worker_method) -> bool:
        """
        Start serial port monitoring process.
        
        Args:
            port: Port identifier (e.g., "ttyACM0" or "Port1" for fake)
            monitor_log_widget: Log widget for output streaming
            gui_run_worker_method: GUI's async worker method (e.g., app.run_worker)
            
        Returns:
            True if started, False if already monitoring this port
        """
        if port in self.active_monitors:
            return False
            
        self.port_loggers[port] = monitor_log_widget
        if port.startswith("Port"):
            command = self._create_fake_monitor_command(port)
        else:
            command = self._create_real_monitor_command(port)
        config = ShellCommandConfig(
            name=f"Monitor {port}",
            command=command
        )
        process = PortMonitorProcess(
            config=config, 
            port_log_widget=monitor_log_widget,
            read_timeout=self.read_timeout,
            chunk_size=self.chunk_size,
            flush_interval=self.flush_interval
        )
        
        self.active_monitors[port] = process
        worker = gui_run_worker_method(
            self.run_monitor_with_cleanup(port),
            name=f"monitor_{port}"
        )
        self.worker_tasks[port] = worker
        
        return True
        
    async def stop_monitor_for_gui(self, port: str) -> bool:
        """
        Stop monitoring on specific port and wait for cleanup.
        
        Args:
            port: Port identifier
            
        Returns:
            True if stopped, False if port was not being monitored
        """
        if port not in self.active_monitors:
            return False
            
        process = self.active_monitors[port]
        await process.terminate()
        if port in self.worker_tasks:
            worker = self.worker_tasks[port]
            try:
                await asyncio.wait_for(worker.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                print(f"Worker for port {port} didn't finish in time")
            except Exception as e:
                print(f"Error waiting for worker: {e}")
            del self.worker_tasks[port]
        
        del self.active_monitors[port]
        if port in self.port_loggers:
            del self.port_loggers[port]
            
        return True
        
    def is_monitoring(self, port: str) -> bool:
        """Check if port is being monitored."""
        return port in self.active_monitors
        
    async def stop_all_monitors(self) -> int:
        """
        Stop all active monitors gracefully.
        
        Returns:
            Count of stopped monitors
        """
        stopped_count = 0
        ports_to_stop = list(self.active_monitors.keys())
        
        for port in ports_to_stop:
            try:
                if await self.stop_monitor_for_gui(port):
                    stopped_count += 1
            except Exception as e:
                print(f"Error stopping monitor for port {port}: {e}")
                
        return stopped_count
        
    def _create_fake_monitor_command(self, port: str) -> str:
        """
        Create command for fake monitor script.
        
        Args:
            port: Fake port identifier (e.g., "Port1")
            
        Returns:
            Shell command string
        """
        script_path = os.path.join(os.path.dirname(__file__), 'fake_monitor_script.py')
        return f"python3 {script_path} {port}"
        
    def _create_real_monitor_command(self, port: str) -> str:
        """
        Create command for real serial port monitoring.
        Uses stty for port configuration and cat for reading.
        
        Args:
            port: Serial port name (e.g., "ttyACM0")
            
        Returns:
            Shell command string
        """
        return f'stty -F /dev/{port} {self.BAUD_RATE} {self.PORT_PARAMS} && cat /dev/{port}'

    async def run_monitor_with_cleanup(self, port: str) -> bool:
        """
        Run monitor process with automatic cleanup on completion.
        Called by GUI worker. Handles success/error logging.
        
        Args:
            port: Port identifier
            
        Returns:
            True if completed successfully (return code 0)
        """
        if port not in self.active_monitors:
            return False
            
        process = self.active_monitors[port]
        port_logger = self.port_loggers.get(port)
        
        try:
            port_logger.write(f"--- Monitor on port {port} starts 🚀 ---\n")
            success = await process.run_end_wait()
            if port in self.active_monitors:
                del self.active_monitors[port]
            if port in self.port_loggers:
                del self.port_loggers[port]
                
            if port_logger:
                if success:
                    port_logger.write(f"\n=== Monitor on port {port} completed successfully ✅ ===\n")
                else:
                    port_logger.write(f"\n!!! Monitor on port {port} finished with errors ❌ !!!\n")
                
            return success
            
        except Exception as e:
            if port_logger:
                port_logger.write(f"Monitor on port {port} failed: {e}\n")
            if port in self.active_monitors:
                del self.active_monitors[port]
            if port in self.port_loggers:
                del self.port_loggers[port]
                
            return False
