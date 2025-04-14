#!/usr/bin/env bash

# Copyright © 2024 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u
dir="${0%/*}/.."
echo 1..1
if out=$("$dir/zygolophodon" --version)
then
    sed -e 's/^/# /' <<< "$out"
    case $out in
        $'zygolophodon 0\n'*)
            echo ok 1;;
        *)
            echo not ok 1;;
    esac
else
    echo not ok 1
fi

# vim:ts=4 sts=4 sw=4 et ft=sh
