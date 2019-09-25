#!/bin/sh

set -ex

cleanup () {
    status=$?
    trap - EXIT TERM INT
    echo "Stopping btw..."
    kill $uwsgi_pid
    wait $uwsgi_pid

    /etc/init.d/nginx stop
    su btw -c"set -ex; \
./manage.py btwworker stop --all; \
./manage.py btwexistdb stop; \
./manage.py btwredis stop"
    /etc/init.d/postgresql stop
    /etc/init.d/nullmailer stop

    # Send TERM to all remaining children of this process.
    pkill -P $$ || true
    wait

    exit $status
}

trap cleanup TERM INT EXIT

/etc/init.d/cron start
/etc/init.d/nullmailer start
/etc/init.d/postgresql start
# Wait until we can connect. Django is not as nice.
until su postgres -c'psql < /dev/null'; do sleep 0.5; done

./scripts/first_run.sh
mkdir -p /var/log/nginx/btw
mkdir -p /var/log/uwsgi/app
# There could be a left-over PID file from an earlier run.
rm -f var/run/btw/*
su btw -c"set -ex \
&& ./manage.py btwredis start \
&& ./manage.py btwexistdb start \
&& ./manage.py btwworker start --all \
&& ./manage.py btwcheck"

# We source the nginx secrets.
. /home/btw/.config/btw/nginx-secrets/${BTW_ENV}

sed s/'${COOKIE_BTW_DEV}'/${COOKIE_BTW_DEV}/g /etc/nginx/templates/btw.in > /etc/nginx/sites-enabled/btw
/etc/init.d/nginx start

uwsgi --ini /etc/uwsgi/apps-enabled/btw.ini --hook-master-start "unix_signal:15 gracefully_kill_them_all" &

uwsgi_pid=$!

wait
