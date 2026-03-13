# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
support for old Python versions
'''

import datetime
import re
import sys

if sys.version_info >= (3, 11):
    datetime_fromisoformat = datetime.datetime.fromisoformat
else:
    def datetime_fromisoformat(d):
        d = re.sub(r'Z\Z', '+00:00', d)
        return datetime.datetime.fromisoformat(d)

__all__ = [
    'datetime_fromisoformat',
]

# vim:ts=4 sts=4 sw=4 et
