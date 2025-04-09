#!/usr/bin/env bash

# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u
pdir="${0%/*}/.."
echo 1..2
xout=$(< "$pdir/README")
xout=${xout#*$'\n   $ zygolophodon --help\n   '}
xout=${xout%%$'\n\n'[^ ]*}
xout=${xout//$'\n   '/$'\n'}
out=$("$pdir/zygolophodon" --help)
if [[ "$out" = "$xout" ]]
then
    echo 'ok 1'
else
    diff -u <(cat <<< "$xout") <(cat <<< "$out") | sed -e 's/^/# /'
    echo 'not ok 1'
fi
xsum=$(sha256sum <<< "$out")
xsum=${xsum%% *}
var='SHA-256(help)'
echo "# $var = $xsum"
declare -i n=2
t_sync()
{
    path="$1"
    line=$(grep -F " $var = " < "$pdir/$path")
    sum=${line##*" $var = "}
    if [[ $sum = $xsum ]]
    then
        echo ok $n "$path"
    else
        echo not ok $n "$path"
    fi
    n+=1
}
t_sync 'doc/zygolophodon.1.in'

# vim:ts=4 sts=4 sw=4 et ft=sh
