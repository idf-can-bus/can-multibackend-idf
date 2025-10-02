#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Custom logging handler for Textual RichLog widget integration.
Bridges Python logging to Textual RichLog with automatic level detection,
source identification, and Rich markup support for colored output.
'''

import logging
import re
from enum import Enum
from textual.widgets import RichLog
from py.log.rich_log_extended import RichLogExtended


class LogSource(Enum):
    """
    Log source enumeration with emoji identifiers.
    Used for visual categorization of log messages in GUI.
    """
    CONFIG = ("⚙️", "CONFIG")
    RECONFIG = ("✏", "RECONFIG")
    COMPILE = ("⚒️", "COMPILE")
    BUILD = ("🔨", "BUILD")
    FLASH = ("⚡", "FLASH")
    SERIAL = ("👁️", "SERIAL")
    FAKE_SERIAL = ("👻", "FAKE_MONITOR")
    PYTHON = ("🐍", "PYTHON")

    def __init__(self, emoji: str, display_name: str):
        self.emoji = emoji
        self.display_name = display_name


class RichLogHandler(logging.Handler):
    """
    Logging handler that outputs to Textual RichLog widget.
    Supports automatic log level detection from message content,
    source identification with emojis, and Rich markup formatting.
    All handlers share single RichLog widget instance.
    """
    registered_loggers = {}
    _rich_log = None
    _level_patterns = {
        logging.ERROR: [
            re.compile(r'\b(error|Error|ERROR)\b'),
            re.compile(r'\b(failed|Failed|FAILED)\b'),
            re.compile(r'\b(exception|Exception|EXCEPTION)\b'),
            re.compile(r'\bE \(\d+\)\b'),  # ESP-IDF error format
        ],
        logging.WARNING: [
            re.compile(r'\b(warning|Warning|WARNING)\b'),
            re.compile(r'\b(warn|Warn|WARN)\b'),
            re.compile(r'\bW \(\d+\)\b'),  # ESP-IDF warning format
        ],
        logging.INFO: [
            re.compile(r'\b(info|Info|INFO)\b'),
            re.compile(r'\bI \(\d+\)\b'),
        ]
    }

    @classmethod
    def set_rich_log(cls, rich_log: RichLog):
        """
        Set shared RichLog widget for all handlers.
        
        Args:
            rich_log: RichLog or RichLogExtended instance
        """
        cls._rich_log = rich_log

    @classmethod
    def get_logger(cls, source: LogSource = LogSource.PYTHON, display_name: str = None):
        """
        Get or create logger for given source.
        Creates singleton loggers per (source, display_name) combination.
        
        Args:
            source: Log source category
            display_name: Optional additional identifier (e.g., port name)
            
        Returns:
            Configured logger instance
        """
        logger_key = (source, display_name)
    
        try:
            return cls.registered_loggers[logger_key]
        except KeyError:
            handler = RichLogHandler(source, display_name)
            logger_name = f"{source.display_name}.{display_name}" if display_name else source.display_name
            logger = logging.getLogger(logger_name)
            for h in logger.handlers[:]:
                logger.removeHandler(h)
            logger.addHandler(handler)
            logger.propagate = False
            cls.registered_loggers[logger_key] = logger
            return logger

    def __init__(
            self,
            source: LogSource = LogSource.PYTHON,
            display_name: str = None,
            extra_color: str = None
    ):
        """
        Initialize logging handler.
        
        Args:
            source: Log source category
            display_name: Optional display name suffix
            extra_color: Optional color override (currently unused)
        """
        super().__init__()
        self._source = source
        self._source_display_name = display_name
        self._extra_color = extra_color

    def emit(self, record: logging.LogRecord):
        """
        Emit log record to RichLog widget.
        
        Args:
            record: Log record to emit
        """
        if self._rich_log:
            record = self._modify_record(record)
            msg = self.format(record)
            self._rich_log.write(msg)
            self._rich_log.refresh()

    def _modify_record(self, record: logging.LogRecord) -> logging.LogRecord:
        """
        Modify record to add source identifier and detect level from content.
        
        Args:
            record: Original log record
            
        Returns:
            Modified log record
        """
        return self._modify_message(
            self._modify_level(record)
        )

    def _modify_message(self, record: logging.LogRecord = None) -> logging.LogRecord:
        """
        Add source emoji and display name prefix to message.
        
        Args:
            record: Log record
            
        Returns:
            Modified record with prefixed message
        """
        if self._source_display_name:
            record.msg = f"{self._source.emoji} {self._source_display_name}: {record.msg}"
        else:
            record.msg = f"{self._source.emoji} {self._source.display_name}: {record.msg}"
        return record

    def _modify_level(self, record: logging.LogRecord = None) -> logging.LogRecord:
        """
        Detect and update log level from message content.
        Currently disabled to avoid unintended level changes.
        
        Args:
            record: Log record
            
        Returns:
            Unmodified record (level detection disabled)
        """
        return record
