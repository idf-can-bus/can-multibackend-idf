#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
ESP32 Flash Tool - Main Application Entry Point

A comprehensive GUI and CLI tool for ESP32 development workflow management.
Features include:
- Interactive Textual-based GUI for library and example selection
- Automatic ESP32 port detection (ttyACM*, ttyUSB*)
- Kconfig.projbuild parsing with dependency validation
- Real-time compilation output with ESP-IDF integration
- SDKconfig file management with backup rotation
- Complete flash workflow: configure -> compile -> upload
- CLI arguments for custom paths and verbose logging
- Modular architecture with separated GUI and business logic

Supports ESP-IDF v5.4.1+ and provides streamlined development experience
for ESP32 CAN bus applications and other embedded projects.
'''

import argparse
import logging


# Import our modules
from py.flash_app_gui import FlashAppGui

def main(logging_level):
    parser = argparse.ArgumentParser(description="ESP32 Flash Tool")
    parser.add_argument('-k', '--kconfig',
                        default="./main/Kconfig.projbuild",
                        help="Path to Kconfig file (default: ./main/Kconfig.projbuild)")
    parser.add_argument('-s', '--sdkconfig',
                        default="./sdkconfig",
                        help="Path to sdkconfig file (default: ./sdkconfig)")
    parser.add_argument('-i', '--idf_setup',
                        default="~/esp/v5.4.1/esp-idf/export.sh",
                        help="Path to script for preparing idf.py enviroment (default: ~/esp/v5.4.1/esp-idf/export.sh)")

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help="Enable verbose logging")

    args = parser.parse_args()

    # Adjust logging level based on verbose flag
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)

    app = FlashAppGui(
        kconfig_path=args.kconfig, 
        sdkconfig_path=args.sdkconfig, 
        idf_setup_path=args.idf_setup,
        logging_level=logging_level)
    app.run()


if __name__ == "__main__":
    logging_level = logging.DEBUG
    main(logging_level)
