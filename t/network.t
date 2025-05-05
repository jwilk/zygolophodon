#!/usr/bin/env bash

# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u

. "${0%/*}/common.sh"

case " $* " in
    *' --network '*)
        ;;
    *)
        plan 0 'use --network to opt in to network testing'
        exit 0
        ;;
esac

normspace()
{
    # shellcheck disable=SC2048,SC2086
    s=$(set -f; printf '%s ' $*)
    printf '%s' "${s% }"
}

urls=()
while read -r line
do
    line=${line%%#*}
    line=$(normspace "$line")
    [[ -n $line ]] || continue
    urls+=("$line")
done < "$tdir/network.urls"

echo "1..${#urls[@]}"
declare -i n=1
for url in "${urls[@]}"
do
    rc=0
    out=$("$prog" --limit=2 "$url") || rc=$?
    sed -e 's/^/# /' <<< "$out"
    if [[ $rc = 0 ]]
    then
        echo ok $n "$url"
    else
        echo not ok $n "$url"
    fi
    n+=1
done

# vim:ts=4 sts=4 sw=4 et ft=sh
