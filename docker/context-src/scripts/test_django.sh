#!/bin/sh

set -ex

cleanup () {
    status=$?
    trap - EXIT TERM INT
    echo "Stopping btw..."
    su btw -c"set -ex; \
./manage.py btwworker stop --all; \
./manage.py btwexistdb stop; \
./manage.py btwredis stop"
    # Send TERM to all children of this process.
    pkill -P $$ || true
    wait
    exit $status
}

trap cleanup TERM INT EXIT

# The call to mitmdump creates a new, non-expired certificate for
# mitmproxy. Otherwise, the tests will fail.
su btw -c"set -ex \
&& ./manage.py btwredis start \
&& ./manage.py btwexistdb start \
&& ./manage.py btwworker start --all \
&& ./manage.py btwcheck \
&& timeout --preserve-status 1 mitmdump -n \
&& make BTW_SKIP_BUILD=1 test-django"

#
# SMOKETEST
#

su btw -c"set -ex \
&& ./manage.py runserver \
& sleep 2 \
&& cd /home/btw/btw-smoketest \
&& scrapy crawl btw -a url=@local -a naked=True \
&& [ -f out/LATEST/CLEAN ] || { cp -rp out /tmp/btw-build-dump; exit 1; }"
