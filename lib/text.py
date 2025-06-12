# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
text support
'''

import os
import re
import textwrap
import unicodedata

columns = int(os.getenv('ZYGOLOPHODON_COLUMNS', '78'))

def wcwidth(ch):
    # poor man's wcwidth(3)
    wd = unicodedata.east_asian_width(ch)
    return 1 + (wd in {'F', 'W'})

def wcswidth(s):
    # poor man's wcswidth(3)
    return sum(map(wcwidth, s))

class Symbol:

    @classmethod
    def get_var(cls, name):
        name = name.upper().replace(' ', '_')
        return f'ZYGOLOPHODON_{name}'

    def __init__(self, name):
        var = self.get_var(name)
        text = os.getenv(var, '*')
        if match := re.fullmatch('(.*):([0-9]+)', text):
            (text, width) = match.groups()
            width = int(width)
        else:
            width = wcswidth(text)
        self._text = text
        self.width = width

    def __str__(self):
        return self._text

class symbols:
    link = Symbol('link symbol')
    paperclip = Symbol('paperclip')

def isolate_bidi(text):
    '''
    * If there are any explicit BDI formatting characters in the text
      (except PDF, which is harmless by itself),
      wrap the text with FSI + PDI.
    * Remove any excess PDIs.
    * Append PDIs to close any stray isolate initiators.
    '''
    #
    # Documentation: https://unicode.org/reports/tr9/
    #   ("Unicode Bidirectional Algorithm")
    #
    n = None  # the number of unclosed isolate initiators,
    # or None if the text doesn't need any BiDi treatment
    def repl(match):
        nonlocal n
        if n is None:
            n = 0
        s = match.group()
        if s in '\N{LRI}\N{RLI}\N{FSI}':
            n += 1
        elif s == '\N{PDI}':
            if n == 0:
                return ''
            n -= 1
        return s
    s = re.sub('[\N{LRE}\N{RLE}\N{LRO}\N{RLO}\N{LRI}\N{RLI}\N{FSI}\N{PDI}]', repl, text)
    if n is not None:
        pdi = (n + 1) * '\N{PDI}'
        s = f'\N{FSI}{s}{pdi}'
    return s

def wrap_text(text, indent='', protect=None):
    # FIXME? BiDi-aware terminals consider newlines as paragraph separators,
    # so line-wrapping may disrupt BiDi.
    text = text.splitlines()
    for line in text:
        yield wrap_line(line, indent=indent, protect=protect)

def wrap_line(line, indent='', protect=None):
    tokens = []
    if protect:
        [prot_start, prot_end] = protect
        assert prot_start
        assert prot_end
        assert '\N{SUB}' not in (prot_start + prot_end)
        prot_re = re.compile(
            '\N{SUB}+|'
            + re.escape(prot_start)
            + '(.*?)'
            + re.escape(prot_end)
        )
        def subst(match):
            nonlocal tokens
            token = match.group()
            tokens += [token]
            n = len(token)
            if match.group(1) is not None:
                n -= 2
            return '\N{SUB}' * n
        line = re.sub(prot_re, subst, line)
    lines = textwrap.wrap(line,
        width=columns,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=False,
    )
    lines = str.join('\n', lines)
    if tokens:
        tokens.reverse()
        def unsubst(match):
            del match
            return tokens.pop()
        lines = re.sub('\N{SUB}+', unsubst, lines)
    assert not tokens
    return lines

# vim:ts=4 sts=4 sw=4 et
