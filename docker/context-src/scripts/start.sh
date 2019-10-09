#!/bin/bash

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

#
# CONFIGURE NULLMAILER
#
. /home/btw/.config/btw/${BTW_ENV}/secrets/nullmailer
echo "${NULLMAILER_HOST} smtp --user=${NULLMAILER_USER} --pass=${NULLMAILER_PASSWORD} --ssl" > /etc/nullmailer/remotes

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

#
# CONFIGURE NGINX
#
. /home/btw/.config/btw/${BTW_ENV}/secrets/nginx

sed s/'${COOKIE_BTW_DEV}'/${COOKIE_BTW_DEV}/g /etc/nginx/templates/btw.in > /etc/nginx/sites-enabled/btw
/etc/init.d/nginx start

uwsgi --ini /etc/uwsgi/apps-enabled/btw.ini --hook-master-start "unix_signal:15 gracefully_kill_them_all" &

uwsgi_pid=$!

DEVELOPMENT=`su btw -c"./manage.py btw print-setting DEVELOPMENT"`
BTW_SITE_NAME=`su btw -c"./manage.py btw print-setting BTW_SITE_NAME"`

if [ ${DEVELOPMENT} != True ]; then
    mail -r root@btw.mangalamresearch.org -s "BTW container started for site ${BTW_SITE_NAME}" root@btw.mangalamresearch.org <<EOF
BTW container started for site ${BTW_SITE_NAME}
EOF
fi

wait
