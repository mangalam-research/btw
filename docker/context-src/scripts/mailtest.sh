#!/bin/sh

#
# This is a test of the mail system inside the docker container.
#
# THIS IS NOT AN AUTOMATED TEST! The test is successfull if the person who
# should get the email sent below actually receives it.
#

set -ex

cleanup () {
    status=$?
    trap - EXIT TERM INT
    /etc/init.d/nullmailer stop
    # Send TERM to all children of this process.
    pkill -P $$
    wait
    exit $status
}

trap cleanup TERM INT EXIT

/etc/init.d/nullmailer start

apt-get update
apt-get install bsd-mailx

mail root@btw.mangalamresearch.org <<EOF
Test from BTW's docker mail test.
EOF
