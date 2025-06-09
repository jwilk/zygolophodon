# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
HTTP client
'''

import errno
import json
import gzip
import http.client
import re
import socket
import ssl
import sys
import urllib.request

def _fmt_url_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return str(exc)
    exc = exc.reason
    if isinstance(exc, socket.gaierror):
        for key, value in vars(socket).items():
            if key[:4] == 'EAI_' and value == exc.errno:
                return f'[{key}] {exc.strerror}'
    if isinstance(exc, ssl.SSLError):
        pass
    elif isinstance(exc, OSError):
        try:
            ec = errno.errorcode[exc.errno]
        except LookupError:
            pass
        else:
            return f'[{ec}] {exc.strerror}'
    return str(exc)

class URLError(RuntimeError):

    def __init__(self, url, reason):
        self.url = url
        self.json = None
        if isinstance(reason, urllib.error.HTTPError) and Response.is_json(reason):
            response = Response(reason, url=url)
            try:
                self.json = json.loads(response.data, object_hook=Dict)
            except (json.JSONDecodeError, UnicodeError):
                pass
        self.reason = reason

    def __str__(self):
        reason = self.reason
        if isinstance(reason, Exception):
            reason = _fmt_url_error(reason)
        return reason

class UserAgent():

    headers = {
        'User-Agent': 'zygolophodon (https://github.com/jwilk/zygolophodon)',
        'Accept-Encoding': 'gzip',
    }

    @classmethod
    def _build_opener(cls):
        handlers = ()
        if sys.version_info < (3, 13):
            # Work-around for <https://github.com/python/cpython/issues/99352>
            # ("urllib.request.urlopen() no longer respects the
            # http.client.HTTPConnection.debuglevel").
            handlers = [
                Handler(debuglevel=http.client.HTTPConnection.debuglevel)
                for Handler in [urllib.request.HTTPHandler, urllib.request.HTTPSHandler]
            ]
        opener = urllib.request.build_opener(*handlers)
        opener.addheaders[:] = cls.headers.items()
        return opener

    @classmethod
    def get(cls, url):
        request = urllib.request.Request(url)
        opener = cls._build_opener()
        try:
            response = opener.open(request)
        except urllib.error.URLError as exc:
            raise URLError(url, exc) from exc
        return Response(response, url=url)

class Response():

    def __init__(self, response, *, url):
        with response:
            content_encoding = response.getheader('Content-Encoding', 'identity')
            data = response.read()
        if content_encoding == 'gzip':
            data = gzip.decompress(data)
        elif content_encoding == 'identity':
            pass
        else:
            raise URLError(url, f'unexpected Content-Encoding: {content_encoding!r}')
        self.data = data
        self.headers = response.headers
        self.url = url

    def is_json(self):
        ct = self.headers.get('Content-Type', '')
        match = re.match(r'application/json(;|\Z)', ct)
        return bool(match)

    @property
    def json(self):
        if not self.is_json():
            raise URLError(self.url, 'error: non-JSON content')
        try:
            data = json.loads(self.data, object_hook=Dict)
        except (json.JSONDecodeError, UnicodeError) as exc:
            msg = f'JSON decoding error: {exc}'
            raise URLError(self.url, msg) from exc
        return data

    @property
    def links(self):
        s = self.headers.get('Link', '')
        data = {}
        regexp = re.compile(r'<([^>]+)>; rel="(\w+)"(?:, |\Z)')
        i = 0
        while i < len(s):
            match = regexp.match(s, i)
            if not match:
                raise URLError(self.url, f'cannot parse Link header field: {s!r}')
            (value, key) = match.groups()
            data[key] = value
            i = match.end()
        return data

class Dict(dict):
    __getattr__ = dict.__getitem__

# vim:ts=4 sts=4 sw=4 et
