# Copyright © 2022-2026 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
zygolophodon CLI
'''

import argparse
import collections
import functools
import http.client
import os
import re
import signal
import sys
import types
import urllib.parse

import lib.compat
import lib.html
import lib.inst
import lib.stdout
import lib.text
import lib.www

import lib.mastodon
import lib.bluesky

from lib.utils import compose

__version__ = '0.1'

prog = argparse.ArgumentParser().prog

def fatal(msg):
    print(f'{prog}: {msg}', file=sys.stderr)
    sys.exit(1)

def fmt_url(url):
    if sys.stdout.isatty():
        return re.sub('(.)', r'_\b\1', url)
    return url

def fmt_user(account):
    name = lib.text.isolate_bidi(account.display_name)
    return f'{name} <{fmt_url(account.url)}>'.lstrip()

def fmt_date(d):
    if isinstance(d, str):
        d = lib.compat.datetime_fromisoformat(d)
    d = d.replace(microsecond=0)
    d = str(d)
    d = re.sub('[+]00:00$', 'Z', d)
    return d

fmt_html = functools.partial(lib.html.fmt_html, fmt_url=fmt_url)

class VersionAction(argparse.Action):
    '''
    argparse --version action
    '''

    def __init__(self, option_strings, dest=argparse.SUPPRESS):
        super().__init__(
            option_strings=option_strings,
            dest=dest,
            nargs=0,
            help='show version information and exit'
        )

    def __call__(self, parser, namespace, values, option_string=None):
        del namespace, values, option_string
        print(f'{parser.prog} {__version__}')
        print('+ Python {0}.{1}.{2}'.format(*sys.version_info))  # pylint: disable=consider-using-f-string
        parser.exit()

def pint(s):
    n = int(s)
    if n > 0:
        return n
    raise ValueError
pint.__name__ = 'positive int'

@compose('\n'.join)
def fmt_addr_help(instance_types):
    templates = collections.defaultdict(dict)
    for instance_type in instance_types:
        for template in instance_type.addr_parser.templates:
            templates[template][instance_type] = True
    for template, tmpl_inst_types in templates.items():
        line = template
        if lib.mastodon.Mastodon not in tmpl_inst_types:
            tmpl_inst_types = str.join(', ', (tp.__name__ for tp in tmpl_inst_types))
            line += f' ({tmpl_inst_types})'
        yield line

def xmain():
    ap = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
    ap.color = False
    if sys.version_info < (3, 10):
        # https://bugs.python.org/issue9694
        ap._optionals.title = 'options'  # pylint: disable=protected-access
    ap.add_argument('--version', action=VersionAction)
    ap.add_argument('-d', '--discover', action='store_true',
        help='visit any URL and see what\'s underneath'
    )
    default_limit = 40
    ap.add_argument('--limit', metavar='N', type=pint, default=default_limit,
        help=f'request at most N posts (default: {default_limit})'
    )
    ap.add_argument('--with-ancestors', action='store_true',
        help='show also post ancestors'
    )
    ap.add_argument('--user-agent', help=argparse.SUPPRESS)
    ap.add_argument('--debug-http', action='store_true', help=argparse.SUPPRESS)
    addr_help = fmt_addr_help(lib.inst.Instance.types)
    ap.add_argument('addr', metavar='ADDRESS', help=addr_help)
    opts = ap.parse_args()
    if opts.debug_http:
        http.client.HTTPConnection.debuglevel = 1
    if opts.user_agent is not None:
        lib.www.UserAgent.headers['User-Agent'] = opts.user_agent
    addr = opts.addr
    if '/' in addr:
        # strip URL fragment
        addr, _ = urllib.parse.urldefrag(addr)
        if opts.discover:
            resp = lib.www.UserAgent.get(addr)
            addr = resp.final_url
    if not (match := lib.inst.parse_addr(addr)):
        ap.error('unsupported address')
    sys.stdout.flush()
    with lib.stdout.install():
        instance = match.instance_type.connect(match.url)
        if match.tag:
            process_tag(instance, match.tag,
                limit=opts.limit,
            )
        elif not match.ident:
            process_user(instance, match.user,
                replies=bool(match.with_replies),
                media=bool(match.media),
                limit=opts.limit,
            )
        else:
            with_context = opts.limit > 1 and not match.embed
            process_post(instance, post_id=match.ident,
                with_replies=with_context,
                with_ancestors=(with_context and opts.with_ancestors),
            )

def plural(i, noun):
    if i != 1:
        noun += 's'
    return f'{i} {noun}'

def process_tag(instance, tag_name, *, limit):
    info = instance.fetch_tag_info(tag_name)
    if info.url:
        print('Location:', fmt_url(info.url))
    else:
        print('Location:', f'(cannot generate URL for tag {tag_name!r})')
    history = info.history
    if history:
        n_posts = sum(int(entry.uses) for entry in history)
        n_users = sum(int(entry.accounts) for entry in history)
        n_posts_today = history[0].uses
        n_days = len(history)
        s_days = plural(n_days, 'day')
        print('Statistics:', f'(last {s_days})')
        print(' ', plural(n_posts, 'post'))
        if n_users > 0:
            print(' ', plural(n_users, 'user'))
        if n_posts > 0:
            print(' ', plural(n_posts_today, 'post'), 'today')
    posts = instance.fetch_tag_posts(tag_name, limit=limit)
    print_posts(posts, separators='=- ')

def process_user(instance, username, *, replies=False, media=False, limit):
    user = instance.fetch_user_by_name(username)
    print('User:', fmt_user(user))
    if user.note:
        print()
        print(fmt_html(user.note))
    seen = set()
    if not (media or replies):
        posts = instance.fetch_user_posts(user, limit=limit, pinned=True)
        def gen_posts():
            for post in posts:
                if not post.pinned:
                    # Snac's Mastodon API yields all posts when we asked for pinned ones:
                    # https://codeberg.org/grunfink/snac2/issues/335
                    # Let's filter out non-pinned posts.
                    continue
                yield post
                seen.add(post.id)
        n = print_posts(gen_posts(), separators='=- ')
        if n >= limit:
            limit = 0
    params = types.SimpleNamespace()
    if media:
        params.only_media=True
    else:
        params.exclude_replies = not replies
    posts = instance.fetch_user_posts(user, limit=limit, **vars(params))
    # Filter out posts that were already printed as pinned:
    posts = (post for post in posts if post.id not in seen)
    print_posts(posts, separators='=- ')

def process_post(instance, post_id, *, with_replies=True, with_ancestors=False):
    post = instance.fetch_post(post_id)
    @functools.cache
    def get_context():
        return instance.fetch_post_context(post_id,
            ancestors=with_ancestors,
            descendants=with_replies,
        )
    if with_ancestors:
        context = get_context()
        print_posts(context.ancestors, hide_in_reply_to=True, separators=' -=')
    print_post(post, hide_in_reply_to=with_ancestors)
    if with_replies:
        context = get_context()
        print_posts(context.descendants, hide_in_reply_to=True, separators='=- ')

def print_separator(ch):
    print()
    print(ch * lib.text.columns)
    print()

def print_posts(posts, *, hide_in_reply_to=False, separators='-- '):
    def print_sep(i):
        ch = separators[i]
        if ch.isspace():
            return
        print_separator(ch)
    n = 0
    for n, post in enumerate(posts, start=1):
        print_sep(n > 1)
        print_post(post, hide_in_reply_to=hide_in_reply_to)
    if n > 0:
        print_sep(-1)
    return n

def normalize_lang(lang):
    if lang is None:
        return 'en'
    if lang.startswith('en-'):
        return 'en'
    return lang

def print_post(post, *, hide_in_reply_to=False):
    if post.location:
        print('Location:', fmt_url(post.location))
    url = post.url or post.uri
    if url and url != post.location:
        print('Origin:', fmt_url(url))
    if post.in_reply_to_id and not hide_in_reply_to:
        if post.in_reply_to_url:
            print('In-Reply-To:', fmt_url(post.in_reply_to_url))
        else:
            print('In-Reply-To:', f'(cannot generate URL for post id {post.in_reply_to_id})')
    if post.pinned:
        pinned = post.pinned
        pin_comment = []
        if isinstance(pinned, str):
            pin_comment = fmt_date(pinned)
            pin_comment = [f'({pin_comment})']
        print('Pinned: yes', *pin_comment)
    if post.account:
        # FIXME in Pleroma?
        # Why is the account information missing
        # for some reblogged posts?
        print('From:', fmt_user(post.account))
    date_comment = []
    if post.edited_at:
        date_comment = 'edited ' + fmt_date(post.edited_at)
        date_comment = [f'({date_comment})']
    print('Date:', fmt_date(post.created_at), *date_comment)
    if normalize_lang(post.language) != 'en':
        print('Language:', post.language)
    if post.reblog:
        print('Reblog: yes')
    print()
    if post.reblog:
        print_post(post.reblog)
    else:
        text = fmt_html(post.content)
        print(text)
    print()
    paperclip = lib.text.symbols.paperclip
    for att in post.media_attachments or ():
        # TODO? Render the images with chafa?
        print(paperclip, fmt_url(att.url))
        print()
        text = att.description or ''
        indent = ' ' * (1 + paperclip.width)
        text = lib.text.wrap_text(text, indent=indent)
        for line in text:
            print(line)
        print()

def main():
    try:
        xmain()
    except lib.www.URLError as exc:
        fatal(f'<{exc.url}>: {exc}')
    except BrokenPipeError:
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGPIPE)
        raise

__all__ = ['main']

# vim:ts=4 sts=4 sw=4 et
