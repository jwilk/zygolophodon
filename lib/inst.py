# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
microblogging instances
'''

import abc
import functools
import re
import types
import urllib.parse

import lib.www

from lib.utils import (
    abstractattribute,
    expand_template,
)

urlquote = functools.partial(urllib.parse.quote, safe='')

class Instance(abc.ABC):

    types = []

    tag_url_template = abstractattribute()

    post_id_regexp = abstractattribute()

    addr_parser = abstractattribute()

    def __init__(self, url, data=None):
        self.url = url
        self.data = data

    @classmethod
    def parse_addr(cls, addr):
        match = cls.addr_parser.parse(addr)  # pylint: disable=no-member
        if not match:
            return None
        if match.user:
            match.user = urllib.parse.unquote(match.user)
        if match.tag:
            match.tag = urllib.parse.unquote(match.tag)
        match.url = f'https://{match.domain}'
        del match.domain
        return match

    @classmethod
    def connect(cls, url):
        return cls(url)

    @abc.abstractmethod
    def fetch_user_by_name(self, name):
        pass

    @abc.abstractmethod
    def fetch_user_posts(self, user, *, limit, **params):
        pass

    @abc.abstractmethod
    def fetch_tag_posts(self, tag_name, *, limit, **params):
        pass

    @abc.abstractmethod
    def fetch_post(self, post_id):
        pass

    @abc.abstractmethod
    def fetch_post_context(self, post_id, ancestors=True, descendants=True):
        pass

    def get_tag_url(self, tag_name):
        template = self.tag_url_template
        if template is None:
            return None
        q_tag = urlquote(tag_name)
        path = expand_template(template, tag=q_tag)
        return f'{self.url}{path}'

    def fetch_tag_info(self, tag_name):
        return lib.www.Dict(
            url=self.get_tag_url(tag_name),
            history=None,
        )

    @classmethod
    def register(cls, instance_type):
        cls.types += [instance_type]
        return instance_type

class AddrParser():

    _groups = set()

    def __init__(self, *templates, discard_prefixes=()):
        self._discard_prefixes = discard_prefixes
        self._raw_templates = templates
        # These are set later by __set_name__(),
        # when assigned to an Instance subclass:
        self.templates = ...
        self._post_id_regexp = ...
        self._regexps = ...

    def __set_name__(self, inst_type, _attr_name):
        self._post_id_regexp = inst_type.post_id_regexp
        self._regexps = []
        self.templates = []
        for template in self._raw_templates:
            if template[0] == '/':
                template = f'https://DOMAIN{template}'
            self._add_template(template)
        del self._discard_prefixes
        del self._raw_templates

    def _add_template(self, template):
        self.templates += [template]
        group2regexp = dict(
            domain=r'[^@/?#\0-\40]+',
            user=r'[^/?#\0-\40]+',
            # FIXME? This is much more lax that USERNAME_RE in <app/models/account.rb>
            tag=r'[^/?#\0-\40]+',
            ident=self._post_id_regexp
        )
        discard = self._discard_prefixes
        def repl_punct(match):
            s = match.group()
            try:
                if s != '.' and re.fullmatch(s, s):
                    return s
            except re.error:
                pass
            return re.escape(s)
        template = re.sub(r'\W', repl_punct, template)
        if discard:
            discard_re = str.join('|', map(re.escape, discard))
            discard_re = f'(?:{discard_re})'
            template = template.replace('/DOMAIN/', f'/DOMAIN/(?:{discard_re}/)*')
        def repl_ident(match):
            s = match.group()
            if match.start() == 0 and s == 'https':
                return s
            if s.isupper():
                group = s
                if group == 'NNNNNN':
                    group = 'IDENT'
                regexp = group2regexp[group.lower()]
            else:
                group = s
                regexp = re.escape(s)
            self._groups.add(group.lower())
            return f'(?P<{group}>{regexp})'
        regexp = re.sub(r'(?<![:|\w])\w+', repl_ident, template)
        regexp = re.compile(regexp)
        self._regexps += [regexp]

    def parse(self, url):
        for regexp in self._regexps:
            if match := re.fullmatch(regexp, url):
                break
        else:
            return None
        data = {group: None for group in self._groups}
        data.update(
            (group, value)
            for group, value in match.groupdict().items()
            if not group.isupper()
        )
        data.update(
            (group.lower(), value)
            for group, value in match.groupdict().items()
            if group.isupper()
        )
        return types.SimpleNamespace(**data)

def parse_addr(addr):
    for instance_type in Instance.types:
        if match := instance_type.parse_addr(addr):
            match.instance_type = instance_type
            return match
    return None

__all__ = [
    'AddrParser',
    'Instance',
    'parse_addr',
]

# vim:ts=4 sts=4 sw=4 et
