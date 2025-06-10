# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
HTML parsing
'''

import html.parser
import re
import sys

import lib.text

class HTMLParser(html.parser.HTMLParser):

    def __init__(self):
        super().__init__()
        class state:
            paras = []
            text = ''
            a_text = ''
            a_href = None
            a_depth = 0
            footnotes = {}
        self.z_state = state

    # FIXME: Add proper support for:
    # * <ol>, <ul>, <li>
    # * <blockquote>
    # * <pre>

    def handle_starttag(self, tag, attrs):
        st = self.z_state
        if tag in {'p', 'ol', 'ul', 'blockquote', 'pre'}:
            while st.a_depth > 0:
                self.handle_endtag('a')
            if st.text:
                st.paras += [st.text]
                st.text = ''
            return
        if tag == 'br':
            if st.a_depth > 0:
                st.a_text += ' '
            else:
                st.text += '\n'
            return
        if tag == 'a':
            if st.a_depth == 0:
                href = dict(attrs).get('href', '')
                # Let's normalize the URL somewhat,
                # as per <https://url.spec.whatwg.org/#concept-basic-url-parser>.
                href = re.sub(r'\A[\0-\40]+|[\0-\40]+\Z|[\n\t]+', '', href)
                st.a_href = href
            st.a_depth += 1
            return

    def handle_endtag(self, tag):
        st = self.z_state
        if tag == 'a':
            if st.a_depth > 0:
                st.a_depth -= 1
            if st.a_depth == 0:
                text = st.a_text
                href = st.a_href
                if re.fullmatch(r'#[\w_]+|@[\w_.-]+(@[\w.-]+)?', text) and st.footnotes.get(text, href) == href:
                    # The above should be close enough to Mastodon's own regexps:
                    # + HASHTAG_RE in <app/models/tag.rb>;
                    # + MENTION_RE in <app/models/account.rb>.
                    assert '\n' not in text
                    st.text += f'\N{STX}{text}\N{ETX}'
                    st.footnotes[text] = href
                else:
                    if href in {text, f'http://{text}', f'https://{text}'}:
                        text = ''
                    else:
                        text = f'[{text}]'
                    assert '\n' not in text
                    st.text += f'{text}<\N{STX}{href}\N{ETX}>'
                st.a_href = ''
                st.a_text = ''
            return
        if tag == 'li':
            if st.a_depth > 0:
                st.a_text += ' '
            else:
                st.text += '\n'
            return

    def handle_data(self, data):
        st = self.z_state
        data = re.sub('[\N{STX}\N{ETX}]', '\N{REPLACEMENT CHARACTER}', data)
        data = re.sub(r'[^\S\N{NBSP}\N{NARROW NO-BREAK SPACE}]+', ' ', data)
        if st.a_depth > 0:
            st.a_text += data
        else:
            st.text += data

    def close(self):
        super().close()
        self.handle_starttag('p', {})

    if sys.version_info < (3, 10):
        def error(self, message):
            # hopefully not reachable
            raise RuntimeError(message)

def fmt_html(data, *, fmt_url=str):
    parser = HTMLParser()
    parser.feed(data)
    parser.close()
    lines = []
    for para in parser.z_state.paras:
        lines += lib.text.wrap_text(para, protect='\N{STX}\N{ETX}')
        lines += ['']
    text = str.join('\n', lines)
    def repl(match):
        [url] = match.groups()
        return fmt_url(url)
    text = re.sub('\N{STX}(.*?)\N{ETX}', repl, text, flags=re.DOTALL)
    lines = [text]
    link_symbol = lib.text.symbols.link
    if parser.z_state.footnotes:
        for footnote, url in parser.z_state.footnotes.items():
            url = fmt_url(url)
            lines += [f'{link_symbol} {footnote}: {url}']
    return str.join('\n', lines)

__all__ = ['fmt_html']

# vim:ts=4 sts=4 sw=4 et
