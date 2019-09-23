#
# ## Variables meant to be overriden ##
#

# Set SKIP_CLEAN_CHECK to non-empty value if you want the Makefile to skip
# checking whether BTW's source is clean. If not set, and the source is not
# clean, your build fails.
SKIP_CLEAN_CHECK?=

# Set BROWSER to the browser you want to test when running the selenium-test
# target.
BROWSER?=

# Set SERVICE to the testing service you want when running the selenium-test
# target. The two choices are "browserstack" and "saucelabs". The default is
# "browserstack".
SERVICE?=browserstack

# You may set SELENIUM_TEST to a specific feature name if you want to run that
# feature.
SELENIUM_TEST?=selenium-test

#
# ## None of the variables below are meant to be overriden ##
#

# This is an executable variable that checks whether the source is clean (does
# not have uncommitted changes). It is meant to be used inside rules, and fails
# the recipe if the check fails. Setting the variable SKIP_CLEAN_CHECK will will
# skip the actual test (and thus is always successful).
CLEAN_CHECK:=$(if $(SKIP_CLEAN_CHECK),,[ -z "$$(git status --porcelain)" ] || \
{ echo 'Repository is not clean!'; exit 1; })

# A variable that can resolve to the values "clean" or "unclean" depending on
# whether the source is clean.
UNCLEAN_FLAG:=$(if $(shell [ -z "$$(git status --porcelain)" ] || echo $$?),unclean,clean)

EXIST_DB_JAR:=exist-installer-5.0.0.jar

# The list of packages we must download in order to build the Docker context.
DOWNLOADS:=\
 libsaxonhe-java_9.9.0.2+dfsg-1_all.deb \
 libdom4j-java_2.1.1-2_all.deb \
 $(EXIST_DB_JAR)

# The location of the download cache. The download cache is where we store
# the packages listed in DOWNLOADS.
DOWNLOAD_CACHE:=download-cache

# The final location of the download cache.
CONTEXT_DOWNLOAD_CACHE:=context/install/download-cache

# The path to each DOWNLOAD in CONTEXT_DOWNLOAD_CACHE
CACHED_DOWNLOADS:=$(DOWNLOADS:%=$(CONTEXT_DOWNLOAD_CACHE)/%)

# The basic command to use to invoke docker.
DOCKER_CMD=sudo DOCKER_BUILDKIT=1 -n docker

#
# In theory the label-schema spec is deprecated in favor of OCI manifest
# annotations. In practice, the tools for manipulating annotations are
# still experimental, so...
#
# We do not store a build-date in the image, because:
#
# 1. It is redundant. `docker inspect` already provides information as to
# when the image was created.
#
# 2. Because the value changes with each invocation of `docker build`,
# it causes the creation of multiple images.
#
# --label org.label-schema.build-date="$$(date -u --rfc-3339=seconds)"
#

# The basic build command for building images.
DOCKER_BUILD=$(DOCKER_CMD) build -f Dockerfile context \
--label org.label-schema.vcs-ref="$$(cat context/btw/DEPLOYED)" \
--label org.mangalamresearch.btw.clean=$(UNCLEAN_FLAG) \
--secret id=btw,src=$(HOME)/.config/btw/secrets/docker_build

# The volumes to mount when running docker run. Different targets override
# it with different values.
DOCKER_MOUNTS=

# The basic run command for running ephemeral images.
DOCKER_RUN=$(DOCKER_CMD) run $(DOCKER_MOUNTS)

# The basic docker-compose command to use.
DOCKER_COMPOSE=sudo DOCKER_BUILDKIT=1 -n docker-compose

# The git describe command to use to get a version tag.
DESCRIBE_CMD=git describe --match 'v*'

# The make targets that make up the context used in development.
DEV_CONTEXT:=static-context src-dev btw-backup btw-smoketest \
 $(CACHED_DOWNLOADS) selenium-bins

# DEPLOY_CONTEXT:=static-context src-deploy btw-backup $(CACHED_DOWNLOADS)

.PHONY: static-context
static-context:
## Build the static part of the Docker context. The static part of the Docker
## context is located in ./context-src.
	rm -rf context
	cp -rp context-src context

.PHONY: btw-backup
btw-backup:
## Incorporate btw-backup into the Docker context. It is **always** taken
## from the published repo.
	rm -rf context/btw-backup
	(cd context; git clone --depth=1 \
	 https://github.com/mangalam-research/btw-backup.git btw-backup)
	(cd context/btw-backup; rm -rf .git)

.PHONY: src-dev
src-dev:
## Incorporate the development sources into the Docker context.
	rm -rf context/btw
	$(CLEAN_CHECK)
	(cd ..; git checkout-index --prefix=docker/context/btw/ -a)
	(cd ..; $(DESCRIBE_CMD)) > context/btw/DEPLOYED

.PHONY: btw-smoketest
btw-smoketest:
## Incorporate btw-smoketest into the Docker context. It is **always** taken
## from the published repo.
	rm -rf context/btw-smoketest
	(cd context; git clone --depth=1 \
	 https://github.com/mangalam-research/btw_smoketest.git btw-smoketest)
	(cd context/btw-smoketest; rm -rf .git)

.PHONY: selenium-bins
selenium-bins:
## Incorporate selenium-bins into the Docker context.
	rm -rf context/selenium-bins
	cp -rp selenium-bins context/selenium-bins

# .PHONY: src-deploy
# src-deploy:
# 	rm -rf context/btw
# 	$(CLEAN_CHECK)
# 	(cd context; git clone --depth=1 https://github.com/mangalam-research/btw.git btw)
# 	(cd context/btw; $(DESCRIBE_CMD) > ./DEPLOYED; rm -rf .git)

.PHONY: base-dev-image
base-dev-image: $(DEV_CONTEXT)
## Build the base development image and tag it btw-base-dev.
## This image is the one used for running basic tests.
	$(DOCKER_BUILD) --target=base -t btw-base-dev

.PHONY: selenium-test-image
selenium-test-image: $(DEV_CONTEXT)
## Build the selenium test image and tag it btw-selenium-test.
## This image is the one used for running the selenium tests.
	$(DOCKER_BUILD) --target=selenium-test -t btw-selenium-test

.PHONY: deploy-image
deploy-image: $(DEV_CONTEXT)
## Build the deployment image and tag it btw-deploy.
	$(DOCKER_BUILD) --target=deploy -t btw-deploy

# The mounts that provide the "docker_build" environment.
DOCKER_BUILD_MOUNTS=\
--mount=type=bind,target=/home/btw/.config/btw/settings/docker_build,$\
src=$$(pwd)/context/settings/docker_build \
--mount=type=bind,target=/home/btw/.config/btw/secrets/docker_build,$\
src=$$HOME/.config/btw/secrets/docker_build \
--mount=type=bind,target=/tmp/btw-build-dump,src=/tmp/btw-build-dump

LIVE_MOUNTS=\
--mount=type=bind,target=/srv/www/btw/btw,src=$$(pwd)/.. \
--mount=type=tmpfs,target=/srv/www/btw/btw/var

.PHONY: test
test: DOCKER_MOUNTS=$(DOCKER_BUILD_MOUNTS)
test: base-dev-image
## Run the basic tests.
	mkdir -p /tmp/btw-build-dump
	$(DOCKER_RUN) --rm -it btw-base-dev /root/scripts/test.sh

.PHONY: live-test
live-test: DOCKER_MOUNTS=$(DOCKER_BUILD_MOUNTS) $(LIVE_MOUNTS)
live-test: base-dev-image
## Run the tests but use the working tree.
	mkdir -p /tmp/btw-build-dump
	$(DOCKER_RUN) --rm -it btw-base-dev /root/scripts/test.sh

SELENIUM_DOCKER_RUN=$(DOCKER_RUN) --rm -it btw-selenium-test \
/root/scripts/selenium-test.sh "$(BROWSER)" "$(SERVICE)" "$(SELENIUM_TEST)"

SELENIUM_TEST_MOUNTS=$(DOCKER_BUILD_MOUNTS) \
--mount=type=bind,target=/srv/www/btw/btw/test_logs,$\
src=$$(pwd)/test-logs/ \
--mount=type=bind,target=/srv/www/btw/btw/local_config,$\
src=$$(pwd)/../local_config

.PHONY: selenium-test
selenium-test: DOCKER_MOUNTS=$(SELENIUM_TEST_MOUNTS)
selenium-test: selenium-test-image
## Run the selenium tests.
	mkdir -p "./test-logs/"
	$(SELENIUM_DOCKER_RUN)

.PHONY: live-selenium-test
live-selenium-test: DOCKER_MOUNTS=$(SELENIUM_TEST_MOUNTS) $(LIVE_MOUNTS)
live-selenium-test: selenium-test-image
## Run the selenium tests but use the working tree.
	mkdir -p "./test-logs/"
	$(SELENIUM_DOCKER_RUN)

# The list of compose files for running the btw-deploy image in a develpment
# environment.
COMPOSE:=$(DOCKER_COMPOSE) -f docker-compose.base.yml -f docker-compose.dev.yml

# The list of compose files for running the btw-deploy image "live".
LIVE_COMPOSE:=$(COMPOSE) -f docker-compose.live.yml

.PHONY: run
run: deploy-image
## Bring up the btw-deploy image locally through docker-compose.
	$(COMPOSE) up

.PHONY: stop
stop-local:
## Stop the btw-deploy image locally.
	$(COMPOSE) stop --timeout=60

.PHONY: cat
cat:
## Show the command that start btw-deploy locally through docker-compose.
	@echo "$(COMPOSE)"

.PHONY: run-live
run-live: deploy-image
## Bring up the btw-deploy image locally through docker-compose, and map
## the source code of BTW to the development directory.
	$(LIVE_COMPOSE) up

.PHONY: stop-live
stop-live:
## Stop the btw-deploy image locally (live variant).
	$(LIVE_COMPOSE) stop --timeout=60

.PHONY: cat-live
cat-live:
## Show the command that start btw-deploy locally through docker-compose, live
## variant.
	@echo "$(LIVE_COMPOSE)"

#
# Rules for downloading the external packages.
#
$(DOWNLOAD_CACHE)/libsaxonhe-java_9.9.0.2+dfsg-1_all.deb:
	mkdir -p $(DOWNLOAD_CACHE)
	cd $(DOWNLOAD_CACHE) && wget http://ftp.us.debian.org/debian/pool/main/s/saxonhe/libsaxonhe-java_9.9.0.2+dfsg-1_all.deb

$(DOWNLOAD_CACHE)/libdom4j-java_2.1.1-2_all.deb:
	mkdir -p $(DOWNLOAD_CACHE)
	cd $(DOWNLOAD_CACHE) && wget http://ftp.us.debian.org/debian/pool/main/d/dom4j/libdom4j-java_2.1.1-2_all.deb

$(DOWNLOAD_CACHE)/$(EXIST_DB_JAR):
	mkdir -p $(DOWNLOAD_CACHE)
	cd $(DOWNLOAD_CACHE) && wget https://bintray.com/existdb/releases/download_file?file_path=$(EXIST_DB_JAR) -O $(notdir $@)

$(CONTEXT_DOWNLOAD_CACHE)/%: $(DOWNLOAD_CACHE)/%
	-mkdir $(dir $@)
	cp -p $< $@
