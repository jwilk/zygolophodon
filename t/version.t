#!/usr/bin/env bash

# Copyright © 2024 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u
dir="${0%/*}/.."
echo 1..3
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

# vim:ts=4 sts=4 sw=4 et ft=sh
