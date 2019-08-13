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

#
# Running first_run does more than what we strictly need. It may be advantageous
# eventually to run a slimmed down version of it just for testing.
#
# For now, we use it so that it runs during formal testing and issues with it
# can be found early.
#
./scripts/first_run.sh

mkdir /root/.btw-backup

cat > /root/.btw-backup/config.py <<EOF
ROOT_PATH="/root/backups/"
S3CMD_CONFIG="/root/.btw-backup/s3cmd-config"
S3_URI_PREFIX="s3://foo/backups/"
EOF

# This is a test config that uses a local install of s3rver
cat > /root/.btw-backup/s3cmd-config <<EOF
[default]
access_key = S3RVER
# access_token = x
add_encoding_exts =
add_headers =
bucket_location = US
ca_certs_file =
cache_file =
check_ssl_certificate = True
check_ssl_hostname = True
cloudfront_host = cloudfront.amazonaws.com
default_mime_type = binary/octet-stream
delay_updates = False
delete_after = False
delete_after_fetch = False
delete_removed = False
dry_run = False
enable_multipart = True
encoding = UTF-8
encrypt = False
expiry_date =
expiry_days =
expiry_prefix =
follow_symlinks = False
force = False
get_continue = False
gpg_command = /usr/bin/gpg
gpg_decrypt = %(gpg_command)s -d --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s
gpg_encrypt = %(gpg_command)s -c --verbose --no-use-agent --batch --yes --passphrase-fd %(passphrase_fd)s -o %(output_file)s %(input_file)s
gpg_passphrase =
guess_mime_type = True
host_base = localhost:4999
host_bucket = localhost:4999
human_readable_sizes = False
invalidate_default_index_on_cf = False
invalidate_default_index_root_on_cf = True
invalidate_on_cf = False
kms_key =
limitrate = 0
list_md5 = False
log_target_prefix =
long_listing = False
max_delete = -1
mime_type =
multipart_chunk_size_mb = 15
multipart_max_chunks = 10000
preserve_attrs = True
progress_meter = True
proxy_host =
proxy_port = 0
put_continue = False
recursive = False
recv_chunk = 65536
reduced_redundancy = False
requester_pays = False
restore_days = 1
secret_key = S3RVER
send_chunk = 65536
server_side_encryption = False
signature_v2 = False
simpledb_host = sdb.amazonaws.com
skip_existing = False
socket_timeout = 300
stats = False
stop_on_error = False
storage_class =
urlencoding_mode = normal
use_https = False
use_mime_magic = True
verbosity = WARNING
website_endpoint = http://%(bucket)s.s3-website-%(location)s.amazonaws.com/
website_error =
website_index = index.html
EOF

# Start s3rver
(cd /root/btw-backup; npm install)

/root/btw-backup/node_modules/.bin/s3rver -p 4999 -s -d /tmp/s3rver &

mkdir /root/.aws
cat > /root/.aws/config <<EOF
[profile btw-backup-test]
region=us-east-1
output=json
EOF

cat > /root/.aws/credentials <<EOF
[btw-backup-test]
aws_access_key_id=S3RVER
aws_secret_access_key=S3RVER
EOF

# Make the bucket
aws s3 --endpoint=http://localhost:4999 --profile=btw-backup-test mb s3://foo

# Needed to connect to postgresql
export PGUSER=postgres

btw-backup fs-init --type tar /srv/www/btw/btw/var/log btw-logs
btw-backup db -g global_db_backups
btw-backup db btw db_backups
btw-backup fs /srv/www/btw/btw/var/log btw_log_backups

# The call to mitmdump creates a new, non-expired certificate for
# mitmproxy. Otherwise, the tests will fail.
su btw -c"set -ex \
&& ./manage.py btwredis start \
&& ./manage.py btwexistdb start \
&& ./manage.py btwworker start --all \
&& ./manage.py btwcheck \
&& timeout --preserve-status 1 mitmdump -n \
&& make BTW_SKIP_BUILD=1 test-django"

su btw -c"set -ex \
&& ./manage.py runserver \
& sleep 2 \
&& cd /home/btw/btw-smoketest \
&& scrapy crawl btw -a url=@local -a naked=True \
&& [ -f out/LATEST/CLEAN ] || { cp -rp out /tmp/btw-build-dump; exit 1; }"
