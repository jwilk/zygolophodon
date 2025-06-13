# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
Bluesky
'''

import html
import re

import lib.www

from lib.inst import (
    AddrParser,
    Instance,
)

from lib.utils import (
    Dict,
    compose,
)

urlquote = lib.www.urlquote

def qre(pattern, flags=0):
    r'''
    re.compile() with additional support for \q<...> escape,
    which is like \Q...\E in Perl.
    '''
    def repl(match):
        (s, esc) = match.groups()
        if esc:
            return esc
        return re.escape(s)
    pattern = re.sub(r'\\q<(.*?)>|(\.)', repl, pattern)
    return re.compile(pattern, flags=flags)

def text2html(s):
    s = html.escape(s)
    s = s.replace('\n', '<br>')
    return s

def decamel(s):
    def subst(match):
        return '_' + match.group().lower()
    s = re.sub('[A-Z]', subst, s)
    return s

class UserAgent(lib.www.UserAgent):

    @classmethod
    def handle_json_error(cls, exc, data):
        try:
            code = data.error
            msg = data.message
        except KeyError:
            return
        assert exc.msg
        exc.msg = f'[{code}] {msg}'

@Instance.register
class Bluesky(Instance):

    # Codebase: https://github.com/bluesky-social/atproto

    tag_url_template = '/hashtag/TAG'

    post_id_regexp = '[2-7a-z]{13}'
    # Source: https://atproto.com/specs/tid
    #
    # Identifiers are base-32 integers:
    #
    #    n = (t << 10) + r
    #
    # where
    #
    #    t is microseconds since 1970;
    #    r are randomish lower bits.
    #
    # In practice, it's always 13 characters.
    #
    # $ export TZ=UTC0
    # $ qalc -t '"1970-01-01" + ((32 ** 12) >> 10) us'
    # "2005-09-05T05:58:04"
    # $ qalc -t '"1970-01-01" + ((32 ** 13) >> 10) us'
    # "3111-09-16T23:09:51"

    addr_parser = AddrParser(
        'https://bsky.app/profile/USER',
        'https://bsky.app/profile/USER/post/IDENT',
        'https://bsky.app/hashtag/TAG',
        # TODO? @USER, or maybe only @USER.bsky.social
    )

    def __init__(self, url):
        super().__init__(url)
        self._did_to_handle = {}

    def _remember_user(self, user):
        try:
            handle = user.handle
        except KeyError:
            return
        self._did_to_handle[user.did] = handle

    @classmethod
    def parse_addr(cls, addr):
        match = super().parse_addr(addr)
        if not match:
            return None
        if match.ident:
            ident = f'at://{match.user}/app.bsky.feed.post/{match.ident}'
            match.ident = ident
        match.url = 'https://bsky.app'
        return match

    def _api_url(self, url, *,  public=True):
        domain = 'api.bsky.app'
        if public:
            domain = f'public.{domain}'
        return f'https://{domain}/xrpc/{url}'

    def _fetch(self, url, *, public=True):
        url = self._api_url(url, public=public)
        return UserAgent.get(url).json

    @compose(''.join)
    def _mastodonize_text(self, text, *, facets=()):
        # FIXME: We convert text to HTML, only to convert HTML to text later on.
        btext = text.encode(errors='surrogatepass')
        def tslice(start, stop=None):
            return btext[start:stop].decode(errors='replace')
        i = 0
        for facet in facets:
            for feature in facet.features:
                tp = feature['$type']
                match = qre(r'\q<app.bsky.richtext.facet>#(\w+)').fullmatch(tp)
                if not match:
                    continue
                [tp] = match.groups()
                fn = getattr(self, f'_mastodonize_text_facet_{tp}', None)
                if not fn:
                    continue
                j = facet.index.byteStart
                k = facet.index.byteEnd
                if i <= j < k:
                    yield text2html(tslice(i, j))
                    yield fn(tslice(j, k), feature)  # pylint: disable=not-callable
                    i = k
        yield text2html(tslice(i))

    def _mastodonize_user(self, user):
        class muser:
            at_did = user.did
            url = f'https://bsky.app/profile/{user.handle}'
            try:
                display_name = user.displayName
            except KeyError:
                display_name = ''
            try:
                note = user.description
            except KeyError:
                note = None
            else:
                note = self._mastodonize_text(note)
        return muser

    def _mastodonize_text_facet_link(self, text, feature):
        if match := qre(r'([^/]+/\S{10,})\q<...>').fullmatch(text):
            [prefix] = match.groups()
            q_prefix = re.escape(prefix)
            if re.fullmatch(fr'https?://{q_prefix}\S+', feature.uri):
                text = feature.uri
        q_url = html.escape(feature.uri)
        q_text = text2html(text)
        return f'<a href="{q_url}">{q_text}</a>'

    def _mastodonize_text_facet_mention(self, text, feature):
        did = feature.did
        user = self._did_to_handle.get(did, did)
        url = f'https://bsky.app/profile/{user}'  # FIXME: duplicate code
        return self._mastodonize_text_facet_link(text, Dict(uri=url))

    def _mastodonize_text_facet_tag(self, text, feature):
        url = self.get_tag_url(feature.tag)
        return self._mastodonize_text_facet_link(text, Dict(uri=url))

    def fetch_user_by_name(self, name):
        # https://docs.bsky.app/docs/api/app-bsky-actor-get-profile
        qname = urlquote(name)
        url = f'app.bsky.actor.getProfile?actor={qname}'
        user = self._fetch(url)
        return self._mastodonize_user(user)

    def _get_post_url(self, uri):
        uri_regexp = qre(fr'at://([^%@/?#\0-\40]+)/\q<app.bsky.feed.post>/({self.post_id_regexp})')
        match = uri_regexp.fullmatch(uri)
        if not match:
            # FIXME?
            return uri
        (user, post_id) = match.groups()
        user = self._did_to_handle.get(user, user)
        return f'https://bsky.app/profile/{user}/post/{post_id}'

    def _mastodonize_embed(self, embed):
        if embed is None:
            return
        tp = embed['$type']
        match = qre(r'\q<app.bsky.embed.>(\w+)#view').fullmatch(tp)
        class bad_att:
            url = 'about:invalid'  # FIXME?
            description = f'(unknown embed type: {tp})'
        if not match:
            yield bad_att
            return
        [tp] = match.groups()
        tp = decamel(tp)
        try:
            fn = getattr(self, f'_mastodonize_embed_{tp}')
        except AttributeError:
            yield bad_att
            return
        yield from fn(embed)

    def _mastodonize_embed_images(self, embed):
        for image in embed.images:
            class att:
                url = image.fullsize
                description = image.alt
            yield att

    def _mastodonize_embed_video(self, embed):
        class att:
            url = embed.playlist
            description = None
        yield att

    def _mastodonize_embed_record(self, embed):
        # FIXME?
        record = embed.record
        try:
            author = record.author
        except KeyError:
            pass
        else:
            self._remember_user(author)
        try:
            descr = record.value.text
        except KeyError:
            descr = None
        class att:
            url = self._get_post_url(record.uri)
            description = descr
        yield att

    def _mastodonize_embed_record_with_media(self, embed):
        # FIXME?
        yield from self._mastodonize_embed(embed.media)
        yield from self._mastodonize_embed_record(embed.record)

    def _mastodonize_embed_external(self, embed):
        # FIXME?
        ext = embed.external
        class att:
            url = ext.uri
            description = f'{ext.title}\n\n{ext.description}'
        yield att

    def _mastodonize_post(self, post, *, reason=None):
        record = post.record
        try:
            embed = post.embed
        except KeyError:
            embed = None
        try:
            in_reply_to_uri = record.reply.parent.uri
        except KeyError:
            _in_reply_to_url = in_reply_to_uri = None
        else:
            _in_reply_to_url = self._get_post_url(in_reply_to_uri)
        _pinned = False
        if reason and reason['$type'] == 'app.bsky.feed.defs#reasonPin':
            _pinned = True
        self._remember_user(post.author)
        try:
            facets = record.facets
        except KeyError:
            facets = ()
        class mpost:
            id = url = location = self._get_post_url(post.uri)
            in_reply_to_id = in_reply_to_url = _in_reply_to_url
            account = self._mastodonize_user(post.author)
            # Editing posts is not supported yet:
            # https://github.com/bluesky-social/social-app/issues/673
            # ("Allow editing posts")
            edited_at = None
            created_at = record.createdAt
            try:
                language = record.langs
            except KeyError:
                language = None
            else:
                language = str.join(', ', language)
            reblog = None
            content = self._mastodonize_text(record.text, facets=facets)
            media_attachments = list(self._mastodonize_embed(embed))
            pinned = _pinned
        if reason and reason['$type'] == 'app.bsky.feed.defs#reasonRepost':
            self._remember_user(reason.by)
            class mrepost:
                id = url = uri = location = None
                in_reply_to_id = in_reply_to_url = None
                account = self._mastodonize_user(reason.by)
                edited_at = None
                created_at = reason.indexedAt
                language = None
                reblog = mpost
                content = None
                media_attachments = None
                pinned = None
            return mrepost
        else:
            return mpost

    def fetch_user_posts(self, user, *, limit, pinned=False, **params):
        # https://docs.bsky.app/docs/api/app-bsky-feed-get-author-feed
        if pinned:
            # It's easier to fetch pinned posts together with non-pinned ones.
            return
        del params
        page_limit = 100  # maximum allowed
        url = f'app.bsky.feed.getAuthorFeed?actor={user.at_did}&filter=posts_and_author_threads&includePins=true'
        rlimit = min(limit, page_limit)
        page_url = f'{url}&limit={rlimit}'
        while limit > 0:
            response = self._fetch(page_url)
            for item in response.feed:
                try:
                    reason = item.reason
                except KeyError:
                    reason = None
                yield self._mastodonize_post(item.post, reason=reason)
            try:
                cursor = response.cursor
            except KeyError:
                break
            limit -= len(response.feed)
            rlimit = min(limit, page_limit)
            next_url = f'{url}&limit={rlimit}&cursor={cursor}'
            assert next_url != page_url
            page_url = next_url

    def fetch_tag_posts(self, tag_name, *, limit, **params):
        # https://docs.bsky.app/docs/api/app-bsky-feed-search-posts
        #
        # FIXME? app.bsky.feed.searchPosts doesn't seem to support paging properly:
        # https://github.com/bluesky-social/atproto/issues/2838
        # ("Calling AppView's searchPosts with a cursor returns a 403 error")
        () = params
        q_tag = urlquote('#' + tag_name)
        url = f'app.bsky.feed.searchPosts?q={q_tag}&limit={limit}&sort=top'
        response = self._fetch(url, public=False)
        for post in response.posts:
            yield self._mastodonize_post(post)

    def _get_post_fetch_url(self, post_id, depth=None, parent_height=None):
        # https://docs.bsky.app/docs/api/app-bsky-feed-get-post-thread
        q_post_id = urlquote(post_id)
        url = f'app.bsky.feed.getPostThread?uri={q_post_id}'
        if depth is not None:
            url += f'&depth={depth}'
        if parent_height is not None:
            url += f'&parentHeight={parent_height}'
        return url

    def fetch_post(self, post_id):
        url = self._get_post_fetch_url(post_id, depth=0, parent_height=0)
        thread = self._fetch(url).thread
        return self._mastodonize_post(thread.post)

    def fetch_post_context(self, post_id, *, ancestors=True, descendants=True):
        # FIXME? This duplicates some of the work of fetch_post().
        context = Dict(ancestors=[], descendants=[])
        if not (ancestors or descendants):
            # shortcut:
            return context
        kwargs = {}
        if not ancestors:
            kwargs.update(parent_height=0)
        if not descendants:
            kwargs.update(depth=0)
        url = self._get_post_fetch_url(post_id, **kwargs)
        thread = self._fetch(url).thread
        if ancestors:
            # pylint: disable=no-member
            parent = thread
            while True:
                try:
                    parent = parent.parent
                except KeyError:
                    break
                context.ancestors += [self._mastodonize_post(parent.post)]
            context.ancestors.reverse()
        if descendants:
            # pylint: disable=no-member
            def add_descendants(thread):
                context.descendants += [self._mastodonize_post(thread.post)]
                try:
                    replies = thread.replies
                except KeyError:
                    return
                for reply in replies:
                    add_descendants(reply)
            for reply in thread.replies:
                add_descendants(reply)
        return context

__all__ = [
    'Bluesky',
]

# vim:ts=4 sts=4 sw=4 et
