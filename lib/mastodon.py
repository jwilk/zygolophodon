# Copyright © 2022-2026 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
Mastodon (and Mastodon-like) instances
'''

import abc
import functools
import re
import urllib.parse

import lib.www

from lib.inst import (
    AddrParser,
    Instance,
)

from lib.utils import (
    Dict,
    abstractattribute,
)

urlquote = lib.www.urlquote

class UserAgent(lib.www.UserAgent):

    @classmethod
    def handle_json_error(cls, exc, data):
        try:
            msg = data.error
        except KeyError:
            return
        assert exc.msg
        exc.msg = msg

class Mastodonoid(Instance):

    post_url_template = abstractattribute()

    @classmethod
    @abc.abstractmethod
    def identify(cls, data):
        pass

    @functools.cached_property
    def api_version(self):
        match = re.match('([0-9]+([.][0-9]+)*)', self.data.version)
        version = match.group()
        version = version.split('.')
        return tuple(int(x) for x in version)

    @classmethod
    def connect(cls, url):
        # https://docs.joinmastodon.org/methods/instance/#v1
        # available since Mastodon v1.1
        #
        # FIXME? v1 is deprecated, but OTOH Mastodon before v4.0
        # and some non-Mastodon instances don't support v2.
        #
        # TODO? Use NodeInfo <https://nodeinfo.diaspora.software/>
        # for identification?
        # But it's only available since Mastodon 3.0.
        instance = Mastodon(url, None)
        data = instance._fetch('instance')  # pylint: disable=protected-access
        inst_types = [
            inst for inst in Instance.types
            if issubclass(inst, Mastodonoid)
        ]
        inst_types.sort(
            key=(lambda t: t.identify(data)),
            reverse=True,
        )
        inst_type = inst_types[0]
        return inst_type(url, data)

    def _api_url(self, url):
        return f'{self.url}/api/v1/{url}'

    def _fetch(self, url):
        url = self._api_url(url)
        return UserAgent.get(url).json

    def fetch_user_by_name(self, name):
        # https://docs.joinmastodon.org/methods/accounts/#lookup
        # available since:
        # - Mastodon v3.4
        # - Pleroma v2.5
        # - Akkoma v2.5
        q_name = urlquote(name)
        return self._fetch(f'accounts/lookup?acct={q_name}')

    def _fetch_posts(self, url, *, limit, **params):
        url = self._api_url(url)
        page_limit = 40  # maximum allowed
        pinned = params.get('pinned', False)
        params['limit'] = min(limit, page_limit)
        q_params = urllib.parse.urlencode(params).lower()
        url += f'?{q_params}'
        while limit > 0:
            response = UserAgent.get(url)
            posts = response.json
            self.fix_posts(posts)
            for post in posts:
                if post.pinned is None:
                    post.pinned = pinned
            yield from posts
            limit -= len(posts)
            next_url = response.links.get('next')
            if next_url is None:
                break
            if not url.startswith(self._api_url('')):
                msg = f'suspicious Link URL: {next_url!r}'
                raise RuntimeError(msg)
            url = re.sub(
                r'(?<=[?&]limit=)\d+(?=&|\Z)',
                str(min(limit, page_limit)),
                next_url
            )

    def fetch_user_posts(self, user, *, limit, **params):
        # https://docs.joinmastodon.org/methods/accounts/#statuses
        # available since Mastodon v2.7
        url = f'accounts/{user.id}/statuses'
        return self._fetch_posts(url, limit=limit, **params)

    def fetch_tag_posts(self, tag_name, *, limit, **params):
        # https://docs.joinmastodon.org/methods/timelines/#tag
        # available since Mastodon v0.1
        q_tag = urlquote(tag_name)
        url = f'timelines/tag/{q_tag}'
        return self._fetch_posts(url, limit=limit, **params)

    def fetch_post(self, post_id):
        # https://docs.joinmastodon.org/methods/statuses/#get
        # available since Mastodon v2.7
        post = self._fetch(f'statuses/{post_id}')
        self.fix_post(post)
        return post

    def fetch_post_context(self, post_id, *, ancestors=True, descendants=True):
        # https://docs.joinmastodon.org/methods/statuses/#context
        # available since Mastodon v0.1
        if not (ancestors or descendants):
            # shortcut:
            return Dict(ancestors=None, descendants=None)
        context = self._fetch(f'statuses/{post_id}/context')
        if ancestors:
            self.fix_posts(context.ancestors)
        else:
            context.ancestors = None
        if descendants:
            self.fix_posts(context.descendants)
        else:
            context.descendants = None
        return context

    def get_post_url(self, *, post_id):
        template = self.post_url_template
        if template is None:
            return None
        return self.expand_url_template(template, ident=post_id)

    def get_fixed_post_url(self, url):
        return url

    def fix_post(self, post):
        irt_url = None
        if post.in_reply_to_id:
            irt_url = self.get_post_url(post_id=post.in_reply_to_id)
        post.in_reply_to_url = irt_url
        try:
            post.edited_at
        except KeyError:
            # * In Mastodon, the attribute is available only since v3.5.0.
            # * FIXME in Pleroma?
            #   Why is the attribute missing for reblogs?
            post.edited_at = None
        if post.reblog:
            self.fix_post(post.reblog)
            if post.url == post.reblog.uri:
                # FIXME in Pleroma?
                # Why is the URL unhelpful?
                post.url = self.get_post_url(post_id=post.id)
            if post.uri == post.reblog.uri:
                post.uri = None
        post.url = self.get_fixed_post_url(post.url)
        try:
            post.pinned
        except KeyError:
            post.pinned = None
        if post.url and post.url.startswith(f'{self.url}/'):
            post.location = post.url
        else:
            post.location = self.get_post_url(post_id=post.id)

    def fix_posts(self, posts):
        for post in posts:
            self.fix_post(post)

    def fetch_tag_info(self, tag_name):
        # https://docs.joinmastodon.org/methods/tags/#get
        # available since Mastodon v4.0
        if self.api_version < (4, 0):
            return Instance.fetch_tag_info(self, tag_name)
        q_tag = urlquote(tag_name)
        url = f'tags/{q_tag}'
        return self._fetch(url)

@Instance.register
class Mastodon(Mastodonoid):

    # Codebase: https://github.com/mastodon/mastodon

    tag_url_template = '/tags/TAG'

    post_url_template = '/statuses/IDENT'

    post_id_regexp = '[0-9]{1,18}'
    # Source: lib/mastodon/snowflake.rb
    #
    # Identifiers are decimal integers:
    #
    #    n = (t << 16) + r
    #
    # where
    #
    #    t is milliseconds since 1970;
    #    r are randomish lower bits.
    #
    # In practice, it's always
    # either 17 digits (until 2018)
    #     or 18 digits (2018-2453).
    #
    # $ export TZ=UTC0
    # $ qalc -t '"1970-01-01" + ((10 ** 16) >> 16) ms'
    # "1974-11-02T01:31:27"
    # $ qalc -t '"1970-01-01" + ((10 ** 17) >> 16) ms'
    # "2018-05-09T15:14:39"
    # $ qalc -t '"1970-01-01" + ((10 ** 18) >> 16) ms'
    # "2453-07-13T08:30:35"
    #
    # However, before Mastodon v2.0,
    # identifiers were sequential 64-bit(?) integers:
    # https://github.com/mastodon/mastodon/commit/468523f4ad85f99d

    addr_parser = AddrParser(
        # mail-like
        '@USER@DOMAIN',
        'USER@DOMAIN',
        # user
        '/@USER',
        '/@USER/media',
        '/@USER/with_replies',
        # post
        '/@USER/NNNNNN',
        '/@USER/NNNNNN/embed',
        # tag
        '/tags/TAG',
        # legacy user-less post
        '/statuses/NNNNNN',
        # offsite redirect pages
        '/redirect/statuses/NNNNNN',
        # URI->URL redirects
        '/users/USER',
        '/users/USER/statuses/NNNNNN',
        #
        discard_prefixes={'deck', 'web'},
    )

    @classmethod
    def identify(cls, data):
        del data
        return 0

    def get_fixed_post_url(self, url):
        q_base_url = re.escape(self.url)
        match = re.fullmatch(q_base_url + '/users/([^/]+)/statuses/([0-9]+)/activity', url or '')
        if match:
            # https://github.com/mastodon/mastodon/issues/34433
            # ("reblogs have wrong url")
            (user, post_id) = match.groups()
            url = f'{self.url}/@{user}/{post_id}'
        return url

@Instance.register
class UntamedMastodonoid(Mastodonoid):

    # fallback for unknown (but known to be unsupported) instance types

    tag_url_template = None

    post_url_template = None

    post_id_regexp = None

    addr_parser = AddrParser()  # dummy

    @classmethod
    def identify(cls, data):
        if re.search(r'\b(compatible|really)\b', data.version):
            return 0.1
        match = re.match('^([0-9]+)[.]', data.version)
        if match is None:
            return 0.1
        [major] = match.groups()
        major = int(major)
        if major < 1:
            # /api/v1/instance was added only in Mastodon 1.1
            # <https://github.com/mastodon/mastodon/commit/6be7bde24378bcb0>
            # so this version is clearly a lie.
            return 0.1
        return -1

@Instance.register
class Iceshrimp(Mastodonoid):

    # Codebase: https://iceshrimp.dev/
    # Forks: https://codeberg.org/catodon/catodon

    tag_url_template = '/tags/TAG'

    post_url_template = '/notes/IDENT'

    post_id_regexp = '[0-9a-z]{16,24}'
    # Source: packages/backend/src/misc/gen-id.ts
    #
    # Identifiers are in the form:
    #
    #    t || r
    #
    # where
    #
    #    t is milliseconds since 2000;
    #    r is randomish, configurable length 8-16.
    #
    # Both are in base-36.
    #
    # The docs say the timestamp is 8 chars long
    # (and the code indeed ensures it's _at least_ 8 chars),
    # but that'll only suffice until 2089.
    #
    # $ export TZ=UTC0
    # $ qalc -t '"2000-01-01" + (36 ** 8) ms'
    # "2089-05-24T17:38:22"

    addr_parser = AddrParser(
        '/notes/IDENT',
    )

    @classmethod
    def identify(cls, data):
        if re.search(r'\b(Iceshrimp|Catodon)\b', data.version):
            return 1
        # FIXME? Should Iceshrimp.NET be considered supported?
        return -1

    def fetch_tag_info(self, tag_name):
        # FIXME in Iceshrimp?
        # The API is not available,
        # despite claimed version 4.2 or so.
        return Instance.fetch_tag_info(self, tag_name)

@Instance.register
class Pleroma(Mastodonoid):

    # Codebase: https://git.pleroma.social/pleroma/pleroma

    tag_url_template = '/tag/TAG'

    post_url_template = '/notice/IDENT'

    post_id_regexp = '[0-9a-zA-Z]{18}'
    # Source: https://git.pleroma.social/pleroma/flake_id
    #
    # Identifiers are base-62 integers:
    #
    #    n = (t << 64) + r
    #
    # where
    #
    #    t is milliseconds since 1970;
    #    r are randomish lower bits.
    #
    # In practice, it's always 18 digits (until 2284).
    #
    # $ export TZ=UTC0
    # $ qalc -t '"1970-01-01" + ((62 ** 17) >> 64) ms'
    # "1975-01-29T11:50:12"
    # $ qalc -t '"1970-01-01" + ((62 ** 18) >> 64) ms'
    # "2284-10-19T13:56:44"

    addr_parser = AddrParser(
        '/notice/IDENT',
        '/tag/TAG',
        # TODO? '/USER'?
        # But eww, that's awfully generic.
        # In the mean time /users/USER works already.
    )

    @classmethod
    def identify(cls, data):
        try:
            data.pleroma
        except KeyError:
            return -1
        return 1

    def fix_post(self, post):
        super().fix_post(post)
        try:
            pinned_at = post.pleroma.pinned_at
        except KeyError:
            # available only since Pleroma v2.4
            pass
        else:
            post.pinned = pinned_at

__all__ = [
    'Iceshrimp',
    'Mastodon',
    'Mastodonoid',
    'Pleroma',
    'UntamedMastodonoid',
]

# vim:ts=4 sts=4 sw=4 et
