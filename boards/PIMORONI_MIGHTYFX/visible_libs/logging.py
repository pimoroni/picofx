# SPDX-FileCopyrightText: 2026 Christopher Parrott for Pimoroni Ltd
#
# SPDX-License-Identifier: MIT
#
# A collection of functions for printing out messages with a selectable level of importance.
# 'level' starts at LOG_INFO for information and warnings, and raises to LOG_DEBUG for diagnostics,
# or lowers to LOG_WARN for warnings alone. Logging can be turned off with LOG_NONE.
#
# To change the level in a program, copy the below lines:
#
#     import logging
#     logging.level = logging.LOG_INFO
#
# Note: micropython-lib's logging library uses the same name as this, so installing it over
# this will break any callers of these functions.

LOG_NONE = 0
LOG_WARN = 1
LOG_INFO = 2
LOG_DEBUG = 3

level = LOG_INFO


def warn(objects="", sep="", end="\n"):
    if level >= LOG_WARN:
        print(objects, sep=sep, end=end)


def info(objects="", sep="", end="\n"):
    if level >= LOG_INFO:
        print(objects, sep=sep, end=end)


def debug(objects="", sep="", end="\n"):
    if level >= LOG_DEBUG:
        print(objects, sep=sep, end=end)
