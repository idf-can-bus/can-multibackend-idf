#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Classes for asynchronous execution and management of system commands,
with real-time output streaming to RichText widgets.
'''
from typing import Callable, Any
import asyncio
import logging
import re
from py.shell_commands.shell_command_config import ShellCommandConfig
# from rich.console import Console
# from rich.text import Text


class ShellCommandProcess:
    """
    Manages the execution of a system command and keeps a registry of all instances.
    Supports asynchronous output streaming, pausing, resuming, and termination.
    """
    _instances = set()

    def __init__(self, config: ShellCommandConfig, logger: logging.Handler):
        """
        Initialize the process manager.
        :param config: Configuration for the system command.
        :param logger: Logger instance to use.
        """
        self.config = config
        self.logger = logger
        self.process = None
        self.running = False
        self.pause_output_flag = False
        # Store output for error detection
        self.stdout_lines = []
        self.stderr_lines = []
        # Rich console for ANSI conversion
        # self.console = Console()

    async def start(self) -> int:
        """Start the system command process asynchronously and stream output."""
        try:
            self.process = await asyncio.create_subprocess_shell(
                self.config.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            self.running = True
            ShellCommandProcess._instances.add(self)
            
            await asyncio.wait_for(
                asyncio.gather(
                    self._read_stream(self.process.stdout, self.stdout_lines),
                    self._read_stream(self.process.stderr, self.stderr_lines)
                ),
                timeout=300
            )            
            
            self.running = False
            ShellCommandProcess._instances.discard(self)
            return self.process.returncode or 0
            
        except asyncio.TimeoutError:
            self.logger.error("Process execution timed out after 5 minutes")
            self.terminate()
            return -1
        except Exception as e:
            self.logger.error(f"Process execution failed: {e}")
            self.terminate()
            return -1

    def _convert_ansi_to_rich_markup(self, text: str) -> str:
        """
        Convert ANSI escape codes to Rich markup.
        
        Args:
            text: Text containing ANSI escape codes
            
        Returns:
            Text with Rich markup instead of ANSI codes
        """
        # ANSI color mapping to Rich markup
        ansi_to_rich = {
            '[0;30m': '[black]',      # Black
            '[0;31m': '[red]',        # Red
            '[0;32m': '[green]',      # Green
            '[0;33m': '[yellow]',     # Yellow
            '[0;34m': '[blue]',       # Blue
            '[0;35m': '[magenta]',    # Magenta
            '[0;36m': '[cyan]',       # Cyan
            '[0;37m': '[white]',      # White
            '[1;30m': '[bold black]', # Bold Black
            '[1;31m': '[bold red]',   # Bold Red
            '[1;32m': '[bold green]', # Bold Green
            '[1;33m': '[bold yellow]',# Bold Yellow
            '[1;34m': '[bold blue]',  # Bold Blue
            '[1;35m': '[bold magenta]',# Bold Magenta
            '[1;36m': '[bold cyan]',  # Bold Cyan
            '[1;37m': '[bold white]', # Bold White
            '[0m': '[/]',             # Reset
            '[1m': '[bold]',          # Bold
            '[22m': '[/bold]',        # Reset bold
        }
        
        # Replace ANSI codes with Rich markup
        result = text
        for ansi_code, rich_markup in ansi_to_rich.items():
            result = result.replace(ansi_code, rich_markup)
        
        # Handle any remaining ANSI codes with generic pattern
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*[mK]')
        result = ansi_pattern.sub('', result)
        
        return result

    async def _read_stream(self, stream, output_list) -> None:
        """
        Asynchronously read lines from a stream and send them to the output callback.
        :param stream: The output stream (stdout or stderr).
        :param output_list: List to store output lines for error detection.
        """
        while self.running and stream:
            if self.pause_output_flag:
                await asyncio.sleep(0.1)
                continue
            line = await stream.readline()
            if not line:
                break
            
            # Decode line
            decoded_line = line.decode("utf-8").strip()
            
            # Store original for error detection
            output_list.append(decoded_line)
            
            # Convert ANSI to Rich markup and log
            rich_line = self._convert_ansi_to_rich_markup(decoded_line)
            try:
                self.logger.info(rich_line)
            except MarkupError as e:
                self.logger.info(decoded_line)
            

    def pause_output(self) -> None:
        """
        Pause streaming output to the output callback.
        """
        self.pause_output_flag = True

    def resume_output(self) -> None:
        """
        Resume streaming output to the output callback.
        """
        self.pause_output_flag = False

    def terminate(self) -> None:
        """
        Terminate the running process and unregister the instance.
        """
        if self.process and self.running:
            self.process.terminate()
            self.running = False
            ShellCommandProcess._instances.discard(self)

    def is_running(self) -> bool:
        """
        Check if the process is still running.
        :return: True if running, False otherwise.
        """
        return self.running and self.process and self.process.returncode is None

    async def run_end_wait(self) -> bool:
        """Start and wait for completion, return True if successful."""
        try:
            return_code = await self.start()

            if return_code != 0:
                self.logger.error(f"Process failed with return code: {return_code}")
                return False
            
            # Check for errors in output even if exit code is 0
            error_in_output, error_line = self._contains_error_in_output()
            if error_in_output:
                self.logger.error(f"Process failed with error in output: '{error_line}'")
                return False
                
            return True
            
        except asyncio.TimeoutError:
            self.logger.error("Process timed out")
            return False
        except Exception as e:
            self.logger.error(f"Process failed: {e}")
            return False

    def _contains_error_in_output(self) -> bool:
        """
        Check if the process output contains error messages.
        
        Returns:
            True if error messages were detected, False otherwise
        """
        # Common error patterns for serial ports and system commands
        error_patterns = [
            r"could not open port",
            r"No such file or directory",
            r"Permission denied",
            r"Device or resource busy",
            r"Connection refused",
            r"Error:",
            r"Failed:",
            r"Exception:",
            r"Traceback",
            r"\[Errno \d+\]",  # System error codes
            r"command not found",
            r"bash:.*: No such file or directory"
        ]
        
        
        # Check both stdout and stderr for error patterns
        all_output = self.stdout_lines + self.stderr_lines
        
        for line in all_output:
            for pattern in error_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.logger.error(f"Error in output line: '{line}' was found with pattern: '{pattern}'")
                    return True, line
                    
        return False, None

    @classmethod
    def terminate_all(cls) -> None:
        """
        Terminate all running processes.
        """
        for proc in list(cls._instances):
            proc.terminate()

    @classmethod
    def get_running_processes(cls) -> list:
        """
        Get a list of all currently running processes.
        :return: List of running ShellCommandProcess instances.
        """
        return [p for p in cls._instances if p.is_running()]

