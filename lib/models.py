# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
Mastodon-shaped data models
'''

import dataclasses
import datetime
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

@dataclass
class User:
    url: str
    display_name: str
    note: typing.Optional[str] = None

@dataclass
class Post:
    # pylint: disable=too-many-instance-attributes
    id: typing.Optional[str]
    url: typing.Optional[str]
    uri: typing.Optional[str]
    location: typing.Optional[str]  # extension
    account: User
    created_at: datetime.datetime
    content: typing.Optional[str]
    in_reply_to_id: typing.Optional[str] = None
    in_reply_to_url: typing.Optional[str] = None  # extension
    edited_at: typing.Optional[datetime.datetime] = None
    language: typing.Optional[str] = None
    reblog: typing.Optional['Post'] = None
    media_attachments: typing.Optional[list] = None
    pinned: typing.Optional[bool] = None

@dataclass
class TagInfo:
    url: str
    history: typing.Optional[list] = None

__all__ = [
    'Attachment',
    'Post',
    'TagInfo',
    'User',
]

# vim:ts=4 sts=4 sw=4 et
