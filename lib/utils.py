# Copyright © 2022-2026 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
misc stuff
'''

import abc
import functools
import re

class Dict(dict):
    __getattr__ = dict.__getitem__

class Promise:

    def __init__(self, fn, *args, **kwargs):
        self._deliver = functools.cache(
            functools.partial(fn, *args, **kwargs)
        )

    def deliver(self):
        if isinstance(self, Promise):
            # This type check may seem weird,
            # but we want Promise.deliver(x) work for any type.
            return self._deliver()
        return self

class TemplateVarError(Exception):

    def __init__(self, *, template, var):
        self.template = template
        self.var = var

    def __str__(self):
        return f'cannot expand {self.var} in template {self.template!r}'

def expand_template(template, **subst):
    def repl(match):
        var = match.group()
        lvar = var.lower()
        try:
            value = subst[lvar]
        except KeyError:
            raise TemplateVarError(template=template, var=var)
        return Promise.deliver(value)
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

__all__ = [
    'Dict',
    'Promise',
    'abstractattribute',
    'compose',
    'expand_template',
]

# vim:ts=4 sts=4 sw=4 et
