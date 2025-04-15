#!/usr/bin/env bash

# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u

. "${0%/*}/common.sh"

echo 1..1
if ! command -v dpkg-parsechangelog > /dev/null
then
    echo 'ok 1 # SKIP missing dpkg-parsechangelog(1)'
    exit
fi
out=$(dpkg-parsechangelog -l"$dir/doc/changelog" --all 2>&1 >/dev/null)
if [[ -z $out ]]
then
    echo ok 1
else
    sed -e 's/^/# /' <<< "$out"
    echo not ok 1
fi

# vim:ts=4 sts=4 sw=4 et ft=sh
