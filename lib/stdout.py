# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

'''
sys.stdout wrapper
'''

import contextlib
import http
import inspect
import io
import os
import shutil
import subprocess
import sys

def find_command(command):
    if shutil.which(command):
        return command
    return None

class StdOut(io.TextIOBase):

    def _install_pager(self):
        if not sys.__stdout__.isatty():
            return
        cmdline = os.getenv('PAGER')
        if cmdline in {'', 'cat'}:
            return
        cmdline = (cmdline
            or find_command('pager')  # Debian:
            # https://www.debian.org/doc/debian-policy/ch-customized-programs.html#editors-and-pagers
            or 'more'  # POSIX:
            # https://pubs.opengroup.org/onlinepubs/007904975/utilities/man.html#tag_04_85_08
        )
        env = None
        if os.getenv('LESS') is None:
            env = dict(env or os.environ, LESS='-FXK')
        self._pager = subprocess.Popen(cmdline, shell=True, stdin=subprocess.PIPE, env=env)  # pylint: disable=consider-using-with
        self._stdout = io.TextIOWrapper(self._pager.stdin,
            encoding=sys.__stdout__.encoding,
            errors=sys.__stdout__.errors,
            line_buffering=True,
        )

    def __init__(self):
        super().__init__()
        self._newlines = 0
        self._pager = None
        self._stdout = sys.__stdout__
        self._install_pager()

    def _get_fp(self):
        if http.client.HTTPConnection.debuglevel:
            # Eww, FIXME in Python?
            # http.client prints debug messages to stdout.
            # Let's redirect them to stderr:
            for frameinfo in inspect.stack(context=0):
                if frameinfo.filename == http.client.__file__:
                    return sys.__stderr__
        return self._stdout

    def write(self, s):
        fp = self._get_fp()
        if fp is self._stdout:
            if s == '':
                return
            if s == '\n':
                if self._newlines == 2:
                    return
                self._newlines += 1
            else:
                self._newlines = int(s[-1] == '\n')
        fp.write(s)

    def flush(self):
        self._get_fp().flush()

    def isatty(self):
        return sys.__stdout__.isatty()

    def __exit__(self, exc_type, exc_value, traceback):
        ret = super().__exit__(exc_type, exc_value, traceback)
        if self._pager:
            self._pager.__exit__(exc_type, exc_value, traceback)
            if exc_type is None and self._pager.returncode != 0:
                msg = 'pager failed'
                raise RuntimeError(msg)
            self._pager = None
            self._stdout = None
        return ret

@contextlib.contextmanager
def install():
    assert sys.stdout is sys.__stdout__
    try:
        with StdOut() as sys.stdout:
            yield
    finally:
        sys.stdout = sys.__stdout__

__all__ = ['install']

# vim:ts=4 sts=4 sw=4 et
