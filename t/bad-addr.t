#!/usr/bin/env bash

# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u

. "${0%/*}/common.sh"

echo 1..2

err=$("$prog" moo 2>&1 >/dev/null) || xs=$?
echo "# exit status $xs"
tname='exit status'
case $xs in
    2) echo "ok 1 $tname";;
    *) echo "not ok 1 $tname";;
esac
sed -e 's/^/# /' <<< $err
tname='error message'
case $err in
    *$'\n''zygolophodon: error: unsupported address')
        echo "ok 2 $tname";;
    *)
        echo "not ok 2 $tname";;
esac

# vim:ts=4 sts=4 sw=4 et ft=sh
