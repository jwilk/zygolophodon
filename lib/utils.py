# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
misc stuff
'''

import abc
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
            raise InternalError(f'cannot expand {key} in template {template!r}') from None
    return re.sub('[A-Z]+', repl, template)

def abstractattribute():
    return abc.abstractmethod(lambda: None)

# vim:ts=4 sts=4 sw=4 et
