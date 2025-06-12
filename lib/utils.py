# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
misc stuff
'''

import abc
import functools
import re

class Dict(dict):
    __getattr__ = dict.__getitem__

class InternalError(RuntimeError):
    pass

def expand_template(template, **subst):
    def repl(match):
        key = match.group()
        lkey = key.lower()
        try:
            return subst[lkey]
        except KeyError:
            msg = f'cannot expand {key} in template {template!r}'
            raise InternalError(msg) from None
    return re.sub('[A-Z]+', repl, template)

def abstractattribute():
    return abc.abstractmethod(lambda: None)

def compose(f):
    def eff(g):
        @functools.wraps(g)
        def f_g(*args, **kwargs):
            return f(g(*args, **kwargs))
        return f_g
    return eff

# vim:ts=4 sts=4 sw=4 et
