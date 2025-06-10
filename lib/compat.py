# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
support for old Python versions
'''

import functools
import sys

if sys.version_info < (3, 9):
    functools.cache = functools.lru_cache(maxsize=None)

# vim:ts=4 sts=4 sw=4 et
