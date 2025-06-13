# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
Mastodon-shaped data models
'''

import dataclasses
import functools
import sys
import typing

dataclass = dataclasses.dataclass
if sys.version_info >= (3, 10):
    dataclass = functools.partial(dataclasses.dataclass, kw_only=True)

@dataclass
class Attachment:
    url: str
    description: typing.Optional[str] = None

__all__ = [
    'Attachment',
]

# vim:ts=4 sts=4 sw=4 et
