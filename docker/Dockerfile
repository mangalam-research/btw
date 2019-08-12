# syntax = docker/dockerfile:experimental

FROM python:3.7.3-slim-stretch AS base

LABEL org.label-schema.schema-version="1.0"

RUN set -ex \
  && apt-get update && apt-get install -y --no-install-recommends \
    apt-transport-https \
    gnupg \
  && rm -rf /var/lib/apt/lists/*

COPY *.list /etc/apt/sources.list.d/

# Using -y with apt-get is not enough to remove all prompts. This is necessary.
ENV DEBIAN_FRONTEND noninteractive

WORKDIR /tmp/docker
RUN \
  --mount=type=bind,target=/tmp/docker,source=./keys \
# Cache the npm packages
  --mount=type=cache,target=/root/.npm/_cacache \
# Cache the apt packages
  --mount=type=cache,target=/var/cache/apt \
  --mount=type=cache,target=/var/lib/apt \
  set -ex \
# We need the man directories in order to install further packages.
  && for i in $(seq 1 8); do mkdir -p "/usr/share/man/man$i"; done \
  && apt-key add tei.key \
  && apt-key add nodesource.key \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
# Required by btw_backup.
    bzip2 \
# Required by `npm ci` later.
    git \
# Required by the dpkg -i install below.
    libicu4j-java \
# Required by the dpkg -i install below.
    libintellij-annotations-java \
    libpq-dev \
# Required to make BTW.
    make \
    nginx-full \
    nodejs \
    nullmailer \
    postgresql \
    rdiff-backup \
    redis-server \
    tei-xsl \
    tei-p5-source \
    trang \
    xsltproc \
  && rm /etc/apt/sources.list.d/* \
# Delete the altered keyring.
  && rm /etc/apt/trusted.gpg \
  && rm -rf /usr/share/doc \
  && rm /etc/nginx/sites-available/default \
  && rm /etc/nginx/sites-enabled/default \
  && npm install -g npm

RUN \
  --mount=type=bind,target=/tmp/docker,source=./install \
# Cache the apt packages
  --mount=type=cache,target=/var/cache/apt \
  --mount=type=cache,target=/var/lib/apt \
  set -ex \
  && useradd -m btw -u 1000 \
  && dpkg -i download-cache/*.deb \
  && apt-get install -f \
  && mkdir /usr/local/eXist-db \
  && mkdir -p /var/eXist-db/btw \
  && chown btw.btw /usr/local/eXist-db \
  && chown -R btw.btw /var/eXist-db/btw \
  && su btw -c "java -jar download-cache/eXist-db-setup-4.7.0.jar -options exist.properties" \
# The installer is buggy and did not install our data in the right place. Move
# it.
  && mv /usr/local/eXist-db/webapp/WEB-INF/data /var/eXist-db/btw \
# The installer also fails to edit the conf.xml file. So we have to fix it.
  && sed -i \
     -e's;files="webapp/WEB-INF/data";files="/var/eXist-db/btw/data";' \
     -e's;journal-dir="webapp/WEB-INF/data";journal-dir="/var/eXist-db/btw/data";' \
     -e's/cacheSize="256M"/cacheSize="600M"/' \
     /usr/local/eXist-db/conf.xml \
# Restrict connections to localhost, and change the default ports to
# avoid clashes with other services.
  && sed -i \
     -e's;<Property name="jetty.http.host" deprecated="jetty.host" />;127.0.0.1;g' \
     -e's;<SystemProperty name="jetty.port" default="8080"/>;<SystemProperty name="jetty.port" default="5000"/>;g' \
     -e's;<SystemProperty name="jetty.ssl.port" deprecated="ssl.port" default="8443"/>;<SystemProperty name="jetty.ssl.port" deprecated="ssl.port" default="5443"/>;g' \
     /usr/local/eXist-db/tools/jetty/etc/jetty-http.xml \
     /usr/local/eXist-db/tools/jetty/etc/jetty-ssl.xml \
  && sed -i -e's/localhost:8080/localhost:5000/g' \
     /usr/local/eXist-db/backup.properties \
     /usr/local/eXist-db/client.properties \
  && mkdir -p /srv/www/btw \
  && chown -R btw.btw /srv/www \
  && mkdir -p /var/log/btw/wed_logs \
  && chown -R btw.btw /var/log/btw \
  && mkdir -p /run/uwsgi/app/btw \
  && chown btw:btw /run/uwsgi/app/btw

COPY nginx/btw /etc/nginx/sites-enabled/
COPY uwsgi/btw.ini /etc/uwsgi/apps-enabled/
COPY btw-backup /root/btw-backup

WORKDIR /srv/www/btw/btw/

# We want to do this as root.
RUN \
# We just mount the requirement files to the same location they will end up.
# Mounting the requirement files instead of doing the copy prior to this RUN
# allows redoing this layer if and only if requirements change. Changes to the
# rest of the project do not require rebuilding this layer.
  --mount=type=bind,target=/srv/www/btw/btw/frozen-requirements.txt,source=./btw/frozen-requirements.txt \
  --mount=type=bind,target=/home/btw/btw-smoketest/requirements.txt,source=./btw-smoketest/requirements.txt \
# Cache the apt packages
  --mount=type=cache,target=/var/cache/apt \
  --mount=type=cache,target=/var/lib/apt \
  set -ex \
# Save the state of apt selections prior to installing the build dependencies.
  && savedAptMark="$(apt-mark showmanual)" \
  && apt-get update \
  && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libstdc++-6-dev \
  && pip install -r frozen-requirements.txt \
  && pip install -r /home/btw/btw-smoketest/requirements.txt \
# Remove pip's cache
  && pip install /root/btw-backup \
  && rm -rf /root/.cache \
# Restore the apt selections to what they were prior to having installed
# the build dependencies and purge them.
  && apt-mark auto '.*' > /dev/null \
  && apt-mark manual $savedAptMark \
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false

COPY --chown=btw:btw btw-smoketest /home/btw/btw-smoketest
COPY --chown=btw:btw btw /srv/www/btw/btw

ENV BTW_ENV docker_build

RUN \
  --mount=type=secret,id=btw,target=/home/btw/.config/btw/secrets/docker_build,uid=1000,gid=1000 \
  --mount=type=bind,target=/home/btw/.config/btw/settings,source=./settings \
# We cannot use this until support for uid/gid is released.
# Drop the rm -rf ~/.npm once we can use this mount.
#  --mount=type=cache,target=/home/btw/.npm/_cacache,uid=1000,gid=1000 \
  set -ex \
# There's a bug in Buildkit that causes WORKDIR to mess up the ownership of the
# directory. A fix seems to have been merged, but when will it be available??
#
# See https://github.com/moby/buildkit/issues/973
#
# For now we do this:
  && chown btw:btw . /home/btw/btw-smoketest \
  && su btw -c"set -ex \
    && npm ci \
    && make \
    && (cd /home/btw/btw-smoketest; npm install)" \
  && rm -rf /home/btw/.npm \
  && rm -rf node_modules \
  && mkdir var/lib/redis \
  && chown btw:btw var/lib/redis \
  && sed -i -E -e'/^local\s+all\s+postgres/s/$/ map=supers/' \
     /etc/postgresql/9.6/main/pg_hba.conf \
  && echo "supers          root                    postgres" >> /etc/postgresql/9.6/main/pg_ident.conf \
  && echo "supers          postgres                postgres" >> /etc/postgresql/9.6/main/pg_ident.conf \
  && mkdir -p /root/backups/global_db_backups \
  && mkdir -p /root/backups/db_backups \
  && mkdir -p /root/backups/btw_log_backups

COPY scripts /root/scripts
COPY nullmailer/remotes /etc/nullmailer/remotes

# Unset it so that we *can* run interactive in the final images.
ENV DEBIAN_FRONTEND=

#
# =====
#

FROM base AS deploy
ENTRYPOINT ["/root/scripts/start.sh"]