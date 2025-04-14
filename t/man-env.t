#!/usr/bin/env python3
# encoding=UTF-8

# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

import ast
import functools
import pathlib
import re
import types

basedir = pathlib.Path(__file__).parent.parent

def contain(ctype=list):
    def wrap(f):
        @functools.wraps(f)
        def new_f(*args, **kwargs):
            return ctype(f(*args, **kwargs))
        return new_f
    return wrap

@contain(set)
def extract_src_vars():
    path = basedir / 'zygolophodon'
    with open(path, encoding='UTF-8') as file:
        src = file.read()
    code = compile(src, path, 'exec')
    mod = types.ModuleType('_')
    exec(code, mod.__dict__)  # pylint: disable=exec-used
    mod_node = ast.parse(src, path)
    for node in ast.walk(mod_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if len(node.args) < 1:
            continue
        if not isinstance(node.args[0], ast.Constant):
            continue
        arg = node.args[0].value
        if isinstance(func, ast.Name) and func.id == 'Symbol':
            yield mod.Symbol.get_var(arg)  # pylint: disable=no-member
            continue
        if isinstance(func, ast.Attribute) and func.attr == 'getenv':
            yield arg
            continue

@contain(set)
def extract_man_vars():
    path = basedir / 'doc/zygolophodon.1.in'
    with open(path, encoding='UTF-8') as file:
        src = file.read()
    match = re.search(r'\n[.]SH ENVIRONMENT\n(.+?\n)[.]SH ', src, re.DOTALL)
    [src] = match.groups()
    for match in re.finditer(r'^[.]TP\n[.]B (\S+)$', src, re.MULTILINE):
        [var] = match.groups()
        yield var

def ok(cond, name, todo=False):
    status = ['not ok', 'ok'][cond]
    todo = ['# TODO'] * (todo and not cond)
    print(status, '-', name, *todo)

def main():
    src_vars = extract_src_vars()
    man_vars = extract_man_vars()
    m = len(src_vars) + len(man_vars)
    print(f'1..{m}')
    for var in src_vars:
        ok(var in man_vars, f'{var} in man', todo=True)
    for var in man_vars:
        ok(var in src_vars, f'{var} in src')

if __name__ == '__main__':
    main()

# vim:ts=4 sts=4 sw=4 et ft=python
