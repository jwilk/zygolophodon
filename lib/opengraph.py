# Copyright © 2026 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
Open Graph support
'''

import html.parser
import sys

class HTMLParser(html.parser.HTMLParser):

    class Stop(Exception):
        pass

    def __init__(self):
        super().__init__()
        self.z_state = {}

    def handle_starttag(self, tag, attrs):
        st = self.z_state
        if tag != 'meta':
            return
        attrs = dict(attrs)
        key = attrs.get('property', '')
        if key[:3] != 'og:':
            return
        key = key[3:]
        value = attrs.get('content', '')
        st[key] = value

    def handle_endtag(self, tag):
        if tag == 'head':
            raise self.Stop

    if sys.version_info < (3, 10):
        def error(self, message):
            # hopefully not reachable
            raise RuntimeError(message)

def extract_og(html_doc):
    if isinstance(html_doc, bytes):
        html_doc = html_doc.decode()
    parser = HTMLParser()
    try:
        parser.feed(html_doc)
        parser.close()
    except HTMLParser.Stop:
        pass
    return parser.z_state

__all__ = ['extract_og']

# vim:ts=4 sts=4 sw=4 et
