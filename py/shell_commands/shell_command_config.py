#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Configuration dataclass for shell command execution.
Stores command name and shell command string for subprocess execution.
'''


class ShellCommandConfig:
    """
    Configuration container for shell command execution.
    Simple dataclass holding command name and command string.
    """
    def __init__(self, name: str, command: str):
        """
        Initialize shell command configuration.
        
        Args:
            name: Human-readable command name for logging
            command: Shell command string to execute
        """
        self.name = name or command
        self.command = command
