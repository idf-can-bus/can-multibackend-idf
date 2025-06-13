#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Custom logging handler for Textual RichLog widget.
Provides real-time log message display in the GUI with proper formatting.
'''

import logging
from textual.widgets import RichLog


class RichLogHandler(logging.Handler):
    """
    Custom logging handler for RichLog
    This class is used to log messages to a RichLog widget
    It is used to display the log messages in a more readable format.
    """

    def __init__(self):
        super().__init__()
        self.rich_log = None

    def set_rich_log(self, rich_log: RichLog):
        self.rich_log = rich_log

    def emit(self, record):
        if self.rich_log:
            msg = self.format(record)
            self.rich_log.write(msg)
            # Force refresh to ensure immediate display
            self.rich_log.refresh() 