#!/usr/bin/env python
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
Background Application for Testing Purposes

This script allows you to specify how many times a atomic (empty) task should be repeated,
the timeout for each execution, and the return value of the task.
'''
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description=__description__)

    repeat_n_times_default = 10
    parser.add_argument('-n', '--repeat_n_times',
                        type=int,
                        default=repeat_n_times_default,
                        help=f"Number of times to repeat the task (default: {repeat_n_times_default})")

    timeout_seconds_default = 0.5
    parser.add_argument('-t', '--timeout_seconds',
                        default=timeout_seconds_default,
                        type=float,
                        help=f"Timeout in seconds for each task execution (default: {timeout_seconds_default})")

    exit_code_default = 0
    parser.add_argument('-e', '--exit_code',
                        default=exit_code_default,
                        type=int,
                        help=f"Return value of the task (default: {exit_code_default})")

    args = parser.parse_args()

    import time
    time_sum = 0.0
    for i in range(args.repeat_n_times):
        # write to stdout
        print(f"stdout: #{i + 1}/{args.repeat_n_times} ({time_sum:.2f} [s]) ...")
        # write to stderr
        print(f"stderr: #{i + 1}/{args.repeat_n_times} ({time_sum:.2f} [s]) ...", file=sys.stderr)
        time.sleep(args.timeout_seconds)
        time_sum += round(args.timeout_seconds, 2)
    exit(args.exit_code)

if __name__ == "__main__":
    main()