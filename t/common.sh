#!/usr/bin/env bash

# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

tdir="${0%/*}"
dir="$tdir/.."
case " $* " in
    *' --installed '*)
        prog='zygolophodon';;
    *)
        prog="$dir/zygolophodon";;
esac

plan()
{
    local extra=''
    if [ $1 -eq 0 ]
    then
        extra=" # SKIP $2"
    fi
    printf '1..%d%s\n' "$1" "$extra"
    printf '# test target = %s\n' "$prog"
}

# vim:ts=4 sts=4 sw=4 et ft=sh
