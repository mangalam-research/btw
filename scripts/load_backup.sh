#!/bin/sh

# This script must be called with root privileges.

set -ex

cleanup () {
    status=$?
    trap - EXIT TERM INT
    /etc/init.d/postgresql stop
    su btw -c"set -ex;
./manage.py btwexistdb stop;
./manage.py btwredis stop;"
    # Send TERM to all children of this process.
    pkill -P $$
    wait
    exit $status
}

trap cleanup TERM INT EXIT

help() {
    echo "$0 [-h|--help] [--binary]"
}

ARGS=`getopt -o h --long help,binary -- "$@"`

eval set -- "$ARGS"

while true; do
    case "$1" in
    -h|--help)
        help
        exit 0
        ;;
    --binary)
        binary=true
        shift
        ;;
    *)
        break
        ;;
    esac
done

# We source the secrets.
. /home/btw/.config/btw/secrets/${BTW_ENV}

dump_path=/restore.dump
restore_list=/tmp/pg_restore.list
if [ $binary ]; then
    [ -f $dump_path ] || { echo "You must map the dump to /restore.dump.";
                           exit 1; }
    chown postgres $dump_path
    # This command will reassign all objects to $DATABASE_USER_NAME
    restore="{ { pg_restore -l $dump_path | grep -v 'COMMENT - EXTENSION' > $restore_list ; } \
 && pg_restore -L $restore_list -d $DEFAULT_DATABASE_NAME \
--no-owner --role=$DATABASE_USER_NAME $dump_path ; }"
else
    restore="psql $DEFAULT_DATABASE_NAME"
fi

/etc/init.d/postgresql start

# Wait until we can connect.
until su postgres -c'psql < /dev/null'; do sleep 0.5; done

su postgres -c"set -ex &&
dropdb $DEFAULT_DATABASE_NAME &&
createdb -O $DATABASE_USER_NAME $DEFAULT_DATABASE_NAME &&
$restore"

su btw -c"set -ex &&
./manage.py btwredis start &&
./manage.py btwexistdb start &&
./manage.py migrate &&
./manage.py btwdb set_site_name &&
./manage.py btwexistdb load"
