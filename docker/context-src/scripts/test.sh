#!/bin/sh

set -ex

cleanup () {
    status=$?
    trap - EXIT TERM INT
    /etc/init.d/postgresql stop
    # Send TERM to all children of this process.
    pkill -P $$ || true
    wait
    exit $status
}

trap cleanup TERM INT EXIT

/etc/init.d/postgresql start

# Wait until we can connect.
until su postgres -c'psql < /dev/null'; do sleep 0.5; done

# This is needed for "live" runs because we map var to a tmpfs which is empty.
mkdir -p var/run/btw var/lib var/log/btw/wed
chown btw:btw -R var

#
# Running first_run does more than what we strictly need. It may be advantageous
# eventually to run a slimmed down version of it just for testing.
#
# For now, we use it so that it runs during formal testing and issues with it
# can be found early.
#
./scripts/first_run.sh

#
# TEST DJANGO EMAIL
#

$(dirname $0)/test_email.sh

#
# TEST BACKUPS
#

$(dirname $0)/test_backups.sh

#
# TEST DJANGO
#

$(dirname $0)/test_django.sh
