#!/usr/bin/env bash

# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

tdir="${0%/*}"
dir="$tdir/.."
prog="${ZYGOLOPHODON_TEST_TARGET:-"$dir/zygolophodon"}"

echo "# test target = $prog"

# vim:ts=4 sts=4 sw=4 et ft=sh
