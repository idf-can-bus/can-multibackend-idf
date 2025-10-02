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
    Custom shell command process that writes directly to log for port monitoring.
    This bypasses the normal logger mechanism for direct output streaming.
    Streams output character by character to avoid blocking GUI.
    """
    
    def __init__(self, config: ShellCommandConfig, port_log_widget, read_timeout: float = 0.01, write_timeout: float = 0.01, buffer_size: int = 50):
        """
        Initialize monitor process with direct output.
        
        Args:
            config: Shell command configuration
            port_log_widget:  widget to write output to
            read_timeout: Timeout for reading from subprocess (seconds)
            write_timeout: Timeout for writing to (seconds)
            buffer_size: Buffer size for output (0 = immediate output, no buffering)
        """
        self.config = config
        self.port_log_widget = port_log_widget
        self.process = None
        self.running = False
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.buffer_size = buffer_size
        
        # Buffer for accumulating characters
        self.stdout_buffer = ""
        self.stderr_buffer = ""
        
    async def start(self) -> int:
        """Start monitor process and stream output directly to RichLog."""
        try:
            self.process = await asyncio.create_subprocess_shell(
                self.config.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.running = True
            
            # Stream stdout and stderr in parallel
            stdout_task = asyncio.create_task(self._stream_output(self.process.stdout, prefix=""))
            stderr_task = asyncio.create_task(self._stream_output(self.process.stderr, prefix="STDERR: "))
            
            # Wait for finish
            await self.process.wait()
            await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)
            
            return self.process.returncode
            
        except Exception as e:
            self._write_to_textarea(f"Process failed: {e}\n")
            return -1
            
    async def _stream_output(self, stream, prefix: str = ""):
        """Stream output from subprocess stream to RichLog widget character by character."""
        try:
            # Choose appropriate buffer
            buffer = self.stdout_buffer if prefix == "" else self.stderr_buffer
            
            while self.running:
                try:
                    # Read with timeout to avoid blocking GUI
                    data = await asyncio.wait_for(stream.read(1), timeout=self.read_timeout)
                    if not data:
                        break
                    
                    # Decode character
                    char = data.decode('utf-8', errors='replace')
                    if char:
                        # Add character to buffer
                        buffer += char
                        
                        # Write buffer when we hit newline or buffer gets too long
                        # If buffer_size is 0, write immediately for each character
                        should_write = (
                            char == '\n' or 
                            (self.buffer_size > 0 and len(buffer) >= self.buffer_size) or
                            (self.buffer_size == 0)
                        )
                        
                        if should_write:
                            await asyncio.wait_for(
                                asyncio.to_thread(self._write_to_textarea, f"{prefix}{buffer}"),
                                timeout=self.write_timeout
                            )
                            buffer = ""  # Clear buffer
                        
                except asyncio.TimeoutError:
                    # Timeout is expected - allows GUI to remain responsive
                    continue
                except Exception as e:
                    self._write_to_textarea(f"Stream error: {e}\n")
                    break
            
            # Write any remaining buffer content
            if buffer:
                await asyncio.wait_for(
                    asyncio.to_thread(self._write_to_textarea, f"{prefix}{buffer}"),
                    timeout=self.write_timeout
                )
                    
        except Exception as e:
            self._write_to_textarea(f"Stream error: {e}\n")
    
    def _write_to_textarea(self, text: str) -> None:
        """Write text to TextArea widget."""
        try:
            # Check if widget has text property (TextArea) or write method (RichLog)
            if hasattr(self.port_log_widget, 'text'):
                # TextArea - append to existing text
                self.port_log_widget.text += text
            else:
                # Fallback for RichLog or other widgets
                self.port_log_widget.write(text)
        except Exception as e:
            # Fallback to print if widget methods fail
            print(f"Error writing to widget: {e}")
    
    async def run_end_wait(self) -> bool:
        """Start and wait for completion, return True if successful."""
        return_code = await self.start()
        return return_code == 0
        
    def terminate(self) -> None:
        """Terminate the running process."""
        if self.process and self.running:
            self.process.terminate()
            self.running = False

class ShellMonitorLogic:
    """
    Shell-based monitor logic using ShellCommandProcess.
    Each port has one ShellCommandProcess that can be started/stopped.
    Provides serial port streaming for GUI.
    Supports both real serial ports and fake monitoring for testing.
    """
    BAUD_RATE = 115200  # Default baud rate for ESP-IDF monitors
    PORT_PARAMS = 'raw -echo -ixon -ixoff -crtscts'

    
    def __init__(
        self, 
        idf_setup_path: str = "~/esp/v5.4.1/esp-idf/export.sh",
        read_timeout: float = 0.01,
        write_timeout: float = 0.01,
        buffer_size: int = 50
    ):
        """
        Initialize monitor logic.
        
        Args:
            idf_setup_path: Path to ESP-IDF setup script
            read_timeout: Timeout for reading from subprocess (seconds)
            write_timeout: Timeout for writing to RichLog (seconds)
            buffer_size: Buffer size for output (0 = immediate output, no buffering)
        """
        self.idf_setup_path = os.path.expanduser(idf_setup_path)
        self.read_timeout = read_timeout
        self.write_timeout = write_timeout
        self.buffer_size = buffer_size
        
        # Active monitor processes - key: port, value: PortMonitorProcess
        self.active_monitors: Dict[str, PortMonitorProcess] = {}
        
        # Mapping port to RichLog widget for serial output
        self.port_loggers: Dict[str, object] = {}  # Changed from RichLogExtended to generic object
    
    def start_monitor_for_gui(self, port: str, monitor_log_widget, gui_run_worker_method) -> bool:
        """
        Start monitoring on given port with GUI integration.
        
        Args:
            port: Port identifier to monitor
            monitor_log_widget: RichLog widget to stream to
            gui_run_worker_method: GUI run_worker method for async execution
            
        Returns:
            True if monitor started successfully, False otherwise
        """
        if port in self.active_monitors:
            return False
            
        # Store port log widget mapping  
        self.port_loggers[port] = monitor_log_widget
        
        # Create monitor command based on port type
        if port.startswith("Port"):
            command = self._create_fake_monitor_command(port)
        else:
            command = self._create_real_monitor_command(port)
            
        # Create ShellCommandConfig
        config = ShellCommandConfig(
            name=f"Monitor {port}",
            command=command
        )
        
        # Create process that writes directly to RichLog
        process = PortMonitorProcess(
            config=config, 
            port_log_widget=monitor_log_widget,
            read_timeout=self.read_timeout,
            write_timeout=self.write_timeout,
            buffer_size=self.buffer_size
        )
        
        # Store process
        self.active_monitors[port] = process
        
        # Start process asynchronously via GUI
        gui_run_worker_method(
            self.run_monitor_with_cleanup(port),
            name=f"monitor_{port}"
        )
        
        return True
        
    def stop_monitor_for_gui(self, port: str) -> bool:
        """
        Stop monitoring on specific port.
        
        Args:
            port: Port identifier to stop monitoring
            
        Returns:
            True if monitor was stopped, False if not found
        """
        if port not in self.active_monitors:
            return False
            
        process = self.active_monitors[port]
        process.terminate()
        del self.active_monitors[port]
        
        # Also clean up port loggers
        if port in self.port_loggers:
            del self.port_loggers[port]
            
        return True
        
    def is_monitoring(self, port: str) -> bool:
        """Check if port is being monitored."""
        return port in self.active_monitors
        
    def stop_all_monitors(self) -> int:
        """
        Stop all active monitor processes.
        
        Returns:
            Number of monitors that were stopped
        """
        stopped_count = 0
        ports_to_stop = list(self.active_monitors.keys())
        
        for port in ports_to_stop:
            try:
                if self.stop_monitor_for_gui(port):
                    stopped_count += 1
            except Exception as e:
                # Log error but continue with other monitors
                print(f"Error stopping monitor for port {port}: {e}")
                
        return stopped_count
        
    def _create_fake_monitor_command(self, port: str) -> str:
        """Create fake monitor command for testing."""
        script_path = os.path.join(os.path.dirname(__file__), 'fake_monitor_script.py')
        return f"python3 {script_path} {port}"
        
    def _create_real_monitor_command(self, port: str) -> str:
        """Create real serial monitor command using idf.py monitor."""
        # replace old version: f"bash -c 'source {self.idf_setup_path} && idf.py -p /dev/{port} monitor'"
        return f'stty -F /dev/{port} {self.BAUD_RATE} {self.PORT_PARAMS} && cat /dev/{port}'

    async def run_monitor_with_cleanup(self, port: str) -> bool:
        """
        Run monitor process and handle cleanup when it finishes.
        This method should be called from GUI's run_worker.
        
        Args:
            port: Port identifier
            
        Returns:
            True if monitor completed successfully, False otherwise
        """
        if port not in self.active_monitors:
            return False
            
        process = self.active_monitors[port]
        
        # Get RichLog widget for this port 
        port_logger = self.port_loggers.get(port)
        
        try:
            if port_logger:
                if hasattr(port_logger, 'text'):
                    port_logger.text += f"--- Monitor on port {port} starts 🚀 ---\n"
                else:
                    port_logger.write(f"--- Monitor on port {port} starts 🚀 ---\n")

            # Run the process and wait for completion
            success = await process.run_end_wait()
            
            # Remove from active monitors
            if port in self.active_monitors:
                del self.active_monitors[port]
                
            # Clean up port loggers as well
            if port in self.port_loggers:
                del self.port_loggers[port]
                
            if port_logger:
                if hasattr(port_logger, 'text'):
                    if success:
                        port_logger.text += f"=== Monitor on port {port} completed successfully ✅ ===\n"
                    else:
                        port_logger.text += f"!!! Monitor on port {port} finished with errors ❌ !!!\n"
                else:
                    if success:
                        port_logger.write(f"=== Monitor on port {port} completed successfully ✅ ===\n")
                    else:
                        port_logger.write(f"!!! Monitor on port {port} finished with errors ❌ !!!\n")
                
            return success
            
        except Exception as e:
            # Process failed with exception
            if port_logger:
                if hasattr(port_logger, 'text'):
                    port_logger.text += f"Monitor on port {port} failed: {e}\n"
                else:
                    port_logger.write(f"Monitor on port {port} failed: {e}\n")
            
            # Clean up
            if port in self.active_monitors:
                del self.active_monitors[port]
            if port in self.port_loggers:
                del self.port_loggers[port]
                
            return False