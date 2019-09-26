#!/bin/bash

set -ex

cleanup () {
    status=$?
    trap - EXIT TERM INT
    echo "Stopping btw..."
    su btw -c"set -ex; \
./manage.py btwexistdb stop"
    /etc/init.d/postgresql stop
    # Send TERM to all children of this process.
    pkill -P $$ || true
    wait
    exit $status
}

trap cleanup TERM INT EXIT

# Make btw a super user for the duration of this test.
echo "supers          btw                postgres" >> /etc/postgresql/9.6/main/pg_ident.conf

/etc/init.d/postgresql start

# Wait until we can connect.
until su postgres -c'psql < /dev/null'; do sleep 0.5; done

browser=$1
service=${2:-browserstack}
test=${3:-selenium-test}

chown btw:btw -R /selenium-bins

# We source the secrets.
. /home/btw/.config/btw/${BTW_ENV}/secrets/btw

# Not a secret.
EXISTDB_HOME_PATH=`su btw -c"./manage.py btw print-setting EXISTDB_HOME_PATH"`

su postgres -c"set -ex &&
psql -c \"CREATE ROLE $DATABASE_USER_NAME WITH LOGIN PASSWORD '$DATABASE_PASSWORD';\" &&
psql -c 'ALTER USER $DATABASE_USER_NAME CREATEDB;'"

# The static files are stored in ../static for deployment but the selenium test
# will search for them in sitestatic. So we add this link to allow the test
# suite to run. We don't run this, if it so happens that sitestatic already
# exists, which would happen when running a development version "live".
[ -e sitestatic ] || ln -s ../static sitestatic

# This is needed for "live" runs because we map var to a tmpfs which is empty.
mkdir -p var/run/btw var/lib var/log/btw/wed
chown btw:btw -R var

su btw -c"set -ex \
&& $EXISTDB_HOME_PATH/bin/client.sh -s -l -u admin -P 'existdbpassword' --xpath 'let \$_ := sm:passwd(\"$BTW_EXISTDB_SERVER_ADMIN_USER\", \"$BTW_EXISTDB_SERVER_ADMIN_PASSWORD\") return \"Ok\"' \
&& PATH=$PATH:/selenium-bins \
&& ./manage.py btwexistdb start \
&& ./manage.py btwexistdb createuser \
&& make BTW_SKIP_BUILD=1 BEHAVE_PARAMS=\"-D browser='$browser' -D service=$service\" $test"
