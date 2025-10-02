#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Module for running shell commands and capturing their output in real-time.
@deprecated: Use py.shell_commands.ShellCommandConfig instead.
'''
import subprocess
import time
import select
from dataclasses import dataclass
from py.log.rich_log_handler import LogSource, RichLogHandler


@dataclass
class ShellCommand:
    """
    Data class representing a shell command to be executed.
    Contains the command string and its expected exit code.
    """
    name: str  # Name of the command, for reporting of results
    command: str
    logger: RichLogHandler


class ShellCommandRunner:
    """
    Class for running shell commands and capturing their output in real-time.
    Supports both stdout and stderr streams.
    """

    def run_commands(self, command_obj_list: [ShellCommand], show_stderr: bool = True) -> int:
        """
        Run a shell command and display its output in real-time.
        
        Args:
            command_obj_list: List of Command to execute in shell
            logger: Logger instance for additional logging
            
        Returns:
            int: Exit code of the executed command
        """

        if not command_obj_list:
            command_logger = RichLogHandler.get_logger(LogSource.PYTHON, "SHELL")
            command_logger.info("All commands executed successfully.")
            return 0
        # Get the first command object from the list
        command_obj = command_obj_list[0]



        command_obj.logger.info(f"Running command: {command_obj.name} ({command_obj.command})")
        process = subprocess.Popen(
            command_obj.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Use binary mode for non-blocking reads
            bufsize=0    # Disable buffering
        )

        # Main loop runs until the process completes
        while process.poll() is None:
            # Wait for data from either stdout or stderr with timeout
            readable, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)

            # Process all available outputs
            for stream in readable:
                # Read all available data from the current stream
                while True:
                    line = stream.readline()
                    if not line:  # No more data available
                        break
                    # Convert binary data to text
                    text = line.decode('utf-8').strip()
                    if stream == process.stdout:
                        command_obj.logger.info(text)
                    else:
                        if show_stderr:
                            command_obj.logger.error(text)
            # Short pause to prevent CPU overload
            time.sleep(0.01)

        # Process has finished, read remaining output
        for line in iter(process.stdout.readline, b''):
            text = line.decode('utf-8').strip()
            command_obj.logger.info(text)
        if show_stderr:
            for line in iter(process.stderr.readline, b''):
                text = line.decode('utf-8').strip()
                command_obj.logger.error(f'text')

        # Close the streams
        process.stdout.close()
        process.stderr.close()

        # Wait for the process to complete and get the exit code
        process.wait()
        if process.returncode != 0:
            command_obj.logger.error(f"\n❌ Command '{command_obj.name}' failed with exit code {process.returncode}\n")
        else:
            command_obj.logger.info(f"\n✅ Command '{command_obj.name}' completed successfully with exit code {process.returncode}\n")

        # If there is a next command, run it recursively
        if (process.returncode==0) :
            time.sleep(0.3)  # Optional delay before running the next command
            return self.run_commands(command_obj_list[1:], show_stderr)

        return process.returncode

