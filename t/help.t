#!/usr/bin/env bash

# Copyright © 2022-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u

. "${0%/*}/common.sh"

echo 1..2
xout=$(< "$dir/README")
xout=${xout#*$'\n   $ zygolophodon --help\n   '}
xout=${xout%%$'\n\n'[^ ]*}
xout=${xout//$'\n   '/$'\n'}
out=$("$prog" --help)
if [[ "$out" = "$xout" ]]
then
    echo 'ok 1'
else
    diff -u <(cat <<< "$xout") <(cat <<< "$out") | sed -e 's/^/# /'
    echo 'not ok 1'
fi
# chop off the part that's auto-generated in the man page anyway:
out=$(sed -e '/^  ADDRESS /,/^$/d' <<< "$out")
xsum=$(sha256sum <<< "$out")
xsum=${xsum%% *}
var='SHA-256(help)'
echo "# $var = $xsum"
declare -i n=2
t_sync()
{
    path="$1"
    line=$(grep -F " $var = " < "$path")
    sum=${line##*" $var = "}
    if [ "$sum" = "$xsum" ]
    then
        echo ok $n "$path"
    else
        echo not ok $n "$path"
    fi
    n+=1
}
if [[ $prog = zygolophodon ]]
then
    man_target=$(man -w $prog)
else
    man_target="$dir/doc/zygolophodon.1.in"
fi
t_sync "$man_target"

# vim:ts=4 sts=4 sw=4 et ft=sh
