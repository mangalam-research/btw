#!/bin/sh

# This script must be called with root privileges.

set -ex

TAG=./var/log/FIRST_RUN

[ -f $TAG ] && exit 0

DEFAULT_DATABASE_NAME=`su btw -c"./manage.py btw print-setting DEFAULT_DATABASE_NAME"`
DATABASE_USER_NAME=`su btw -c"./manage.py btw print-setting DATABASE_USER_NAME"`
DATABASE_PASSWORD=`su btw -c"./manage.py btw print-setting DATABASE_PASSWORD"`
DATABASE_PASSWORD=`su btw -c"./manage.py btw print-setting DATABASE_PASSWORD"`
BTW_EXISTDB_SERVER_ADMIN_USER=`su btw -c"./manage.py btw print-setting BTW_EXISTDB_SERVER_ADMIN_USER"`
BTW_EXISTDB_SERVER_ADMIN_PASSWORD=`su btw -c"./manage.py btw print-setting BTW_EXISTDB_SERVER_ADMIN_PASSWORD"`
EXISTDB_HOME_PATH=`su btw -c"./manage.py btw print-setting EXISTDB_HOME_PATH"`

su postgres -c"set -ex &&
psql -c \"CREATE ROLE $DATABASE_USER_NAME WITH LOGIN PASSWORD '$DATABASE_PASSWORD';\" &&
psql -c 'ALTER USER $DATABASE_USER_NAME CREATEDB;' &&
createdb -O $DATABASE_USER_NAME $DEFAULT_DATABASE_NAME"

su btw -c"set -ex &&
$EXISTDB_HOME_PATH/bin/client.sh -s -l -u admin -P '\$adminPasswd' --xpath 'let \$_ := sm:passwd(\"$BTW_EXISTDB_SERVER_ADMIN_USER\", \"$BTW_EXISTDB_SERVER_ADMIN_PASSWORD\") return \"Ok\"'
./manage.py btwredis start &&
./manage.py migrate &&
./manage.py btwdb set_site_name &&
./manage.py btwexistdb start &&
./manage.py btwexistdb createuser &&
./manage.py btwexistdb createdb &&
./manage.py btwexistdb loadindex &&
./manage.py btwexistdb load &&
./manage.py btwexistdb loadutil &&
./manage.py btwexistdb stop &&
./manage.py btwredis stop &&
touch $TAG"
