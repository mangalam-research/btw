#!/bin/sh

set -ex

cleanup () {
    status=$?
    trap - EXIT TERM INT
    echo "Stopping btw..."
    su btw -c"set -ex; \
./manage.py btwredis stop"
    # Send TERM to all children of this process.
    pkill -P $$ || true
    wait
    exit $status
}

trap cleanup TERM INT EXIT

su btw -c"set -ex \
&& ./manage.py btwredis start \
&& ./manage.py email_integration_test"
