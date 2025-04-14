#!/usr/bin/env bash

# Copyright © 2024-2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u
dir="${0%/*}/.."
echo 1..4
IFS='(); ' read -r _ changelog_version changelog_dist _ < "$dir/doc/changelog"
echo "# changelog version = $changelog_version"
echo "# changelog dist = $changelog_dist"
if out=$("$dir/zygolophodon" --version)
then
    echo ok 1
    sed -e 's/^/# /' <<< "$out"
    case $out in
        $"zygolophodon $changelog_version"$'\n'*)
            echo ok 2;;
        *)
            echo not ok 2;;
    esac
else
    echo not ok 1
    echo not ok 2
fi
if [ -d "$dir/.git" ]
then
    echo 'ok 3 # skip git checkout'
elif [ "$changelog_dist" = UNRELEASED ]
then
    echo 'not ok 3'
else
    echo 'ok 3'
fi
man_target="$dir/doc/zygolophodon.1"
echo "# man page target = $man_target"
if [[ -f $man_target ]]
then
    line=$(MANWIDTH=80 man "$man_target" | tail -n 1)
    IFS=' "' read -r _ man_version _ <<< "$line"
    echo "# man page version = $man_version"
    if [[ $man_version = $changelog_version ]]
    then
        echo ok 4
    else
        echo not ok 4
    fi
else
    echo 'ok 4 # skip missing man page'
fi

# vim:ts=4 sts=4 sw=4 et ft=sh
