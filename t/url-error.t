#!/bin/sh

# Copyright © 2025 Jakub Wilk <jwilk@jwilk.net>
# SPDX-License-Identifier: MIT

set -e -u
pdir="${0%/*}/.."
echo 1..2
unshare_net()
{
    unshare --user --net "$@"
}
if ! unshare_net true 2>/dev/null
then
    unshare_net()
    {
        "$@"
    }
fi
export http_proxy='http://127.0.0.1:9/'
export https_proxy="$http_proxy"
export RES_OPTIONS=attempts:0
xc=0
base_url=https://mastodon.social
url="$base_url/@Mastodon"
echo "# $url"
err=$(unshare_net "$pdir/zygolophodon" "$url" 2>&1 >/dev/null) || xs=$?
echo "# exit status $xs"
tname='exit status'
case $xs in
    1) echo "ok 1 $tname";;
    *) echo "not ok 1 $tname";;
esac
echo "# $err"
tname='error message'
case $err in
    "zygolophodon: <$base_url/api/v1/instance>: [E"[A-Z]*'] '*)
        echo "ok 2 $tname";;
    *)
        echo "not ok 2 $tname";;
esac

# vim:ts=4 sts=4 sw=4 et ft=sh
