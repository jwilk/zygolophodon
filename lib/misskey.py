# Copyright © 2026 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
Misskey
'''

# Codebase: https://github.com/misskey-dev/misskey
# Forks: https://activitypub.software/TransFem-org/Sharkey

import html.parser
import json
import sys

import lib.compat

from lib.models import (
    Attachment,
    Post,
)

from lib.utils import (
    Dict,
)

from lib.www import UserAgent

class HTMLParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        class state:
            data = None
            depth = 0
        self.z_state = state

    def handle_starttag(self, tag, attrs):
        st = self.z_state
        if st.depth > 0:
            st.depth += 1
            return
        if tag == 'script':
            attrs = dict(attrs)
            if attrs.get('id') == 'misskey_clientCtx':
                st.data = ''
                st.depth = 1

    def handle_endtag(self, tag):
        st = self.z_state
        if st.depth > 0:
            st.depth -= 1

    def handle_data(self, data):
        st = self.z_state
        if st.depth > 0:
            st.data += data

    if sys.version_info < (3, 10):
        def error(self, message):
            # hopefully not reachable
            raise RuntimeError(message)

def _extract_note(html_doc):
    if isinstance(html_doc, bytes):
        html_doc = html_doc.decode()
    parser = HTMLParser()
    parser.feed(html_doc)
    parser.close()
    data = parser.z_state.data
    data = json.loads(data, object_hook=Dict)
    return data.note

def _mastodonize_files(files):
    for file in files:
        yield Attachment(
            url=file.url,
            description=file.comment,
        )

def _mastodonize_note(inst, note):
    created_at = lib.compat.datetime_fromisoformat(note.createdAt)
    try:
        edited_at = note.updatedAt
    except KeyError:
        edited_at = None
    else:
        edited_at = lib.compat.datetime_fromisoformat(edited_at)
    username = note.user.username
    if note.user.host is not None:
        # FIXME?
        username += f'@{note.user.host}'
    user_url = inst.get_user_url(username=username)
    user = lib.models.User(
        url=user_url,
        display_name=note.user.name,
    )
    in_reply_to_id = None
    in_reply_to_url = None
    location = inst.get_post_url(post_id=note.id)
    try:
        uri = note.uri
    except KeyError:
        uri = None
    try:
        url = note.url
    except KeyError:
        url = None
    if note.replyId is not None:
        in_reply_to_id = note.replyId
        in_reply_to_url = inst.get_post_url(post_id=in_reply_to_id)
    content = None
    if note.text is not None:
        content = lib.html.text2html(note.text)  # FIXME: lost formatting
    try:
        renote = note.renote
    except KeyError:
        reblog = None
    else:
        reblog = _mastodonize_note(inst, renote)
    atts = list(_mastodonize_files(note.files))
    return Post(
        id=note.id,
        url=uri,
        uri=url,
        location=location,
        account=user,
        created_at=created_at,
        content=content,
        in_reply_to_id=in_reply_to_id,
        in_reply_to_url=in_reply_to_url,
        edited_at=edited_at,
        # FIXME? language=
        reblog=reblog,
        media_attachments=atts,
        # FIXME? pinned=
    )

def fetch_post(inst, post_id):
    url = inst.get_post_url(post_id=post_id)
    html_doc = UserAgent.get(url).data
    note = _extract_note(html_doc)
    return _mastodonize_note(inst, note)

__all__ = ['fetch_post']

# vim:ts=4 sts=4 sw=4 et
