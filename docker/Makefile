
CLEAN_CHECK:=$(if $(SKIP_CLEAN_CHECK),,[ -z "$$(git status --porcelain)" ] || \
{ echo 'Repository is not clean!'; exit 1; })
UNCLEAN_FLAG:=$(if $(shell [ -z "$$(git status --porcelain)" ] || echo $$?),unclean,clean)

DOWNLOADS:=libsaxonhe-java_9.9.0.2+dfsg-1_all.deb libdom4j-java_2.1.1-2_all.deb eXist-db-setup-4.7.0.jar

DOWNLOAD_CACHE:=download-cache/
CONTEXT_DOWNLOAD_CACHE:=context/install/download-cache
CACHED_DOWNLOADS:=$(DOWNLOADS:%=$(CONTEXT_DOWNLOAD_CACHE)/%)

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
DOCKER_BUILD=$(DOCKER_CMD) build -f Dockerfile context \
--label org.label-schema.vcs-ref="$$(cat context/btw/DEPLOYED)" \
--label org.mangalamresearch.btw.clean=$(UNCLEAN_FLAG) \
--secret id=btw,src=$(HOME)/.config/btw/secrets/docker_build

DOCKER_RUN=$(DOCKER_CMD) run

DOCKER_COMPOSE=sudo DOCKER_BUILDKIT=1 -n docker-compose

DESCRIBE_CMD=git describe --match 'v*'

.PHONY: context
context:
	rm -rf context
	cp -rp context-src context

.PHONY: btw-backup
btw-backup:
	rm -rf context/btw-backup
	(cd context; git clone --depth=1 https://github.com/mangalam-research/btw-backup.git btw-backup)
	(cd context/btw-backup; rm -rf .git)

.PHONY: src-dev
src-dev:
	rm -rf context/btw
	$(CLEAN_CHECK)
	(cd ..; git checkout-index --prefix=docker/context/btw/ -a)
	(cd ..; $(DESCRIBE_CMD)) > context/btw/DEPLOYED

.PHONY: btw-smoketest
btw-smoketest:
	rm -rf context/btw-smoketest
	(cd context; git clone --depth=1 https://github.com/mangalam-research/btw_smoketest.git btw-smoketest)
	(cd context/btw-smoketest; rm -rf .git)

# .PHONY: src-deploy
# src-deploy:
# 	rm -rf context/btw
# 	$(CLEAN_CHECK)
# 	(cd context; git clone --depth=1 https://github.com/mangalam-research/btw.git btw)
# 	(cd context/btw; $(DESCRIBE_CMD) > ./DEPLOYED; rm -rf .git)

DEV_CONTEXT:=context src-dev btw-backup btw-smoketest $(CACHED_DOWNLOADS)
# DEPLOY_CONTEXT:=context src-deploy btw-backup $(CACHED_DOWNLOADS)

.PHONY: base-dev
base-dev: $(DEV_CONTEXT)
	$(DOCKER_BUILD) --target=base -t btw-base-dev

.PHONY: test
test: base-dev
	mkdir -p /tmp/btw-build-dump
	$(DOCKER_RUN) \
	--mount=type=bind,target=/home/btw/.config/btw/settings/docker_build,\
	source=$$(pwd)/context/settings/docker_build \
	--mount=type=bind,target=/home/btw/.config/btw/secrets/docker_build,\
	source=$$HOME/.config/btw/secrets/docker_build \
        --mount=type=bind,target=/tmp/btw-build-dump,src=/tmp/btw-build-dump \
	--rm -it btw-base-dev /root/scripts/test.sh

.PHONY: local-deploy
local-deploy: $(DEV_CONTEXT)
	$(DOCKER_BUILD) --target=deploy -t btw-deploy

LOCAL_COMPOSE:=$(DOCKER_COMPOSE) -f docker-compose.base.yml -f docker-compose.dev.yml
LIVE_COMPOSE:=$(LOCAL_COMPOSE) -f docker-compose.live.yml

.PHONY: run-local
run-local: local-deploy
	$(LOCAL_COMPOSE) up

.PHONY: run-live
run-live: local-deploy
	$(LIVE_COMPOSE) up

.PHONY: stop-local
stop-local:
	$(LOCAL_COMPOSE) stop --timeout=60

.PHONY: stop-live
stop-live:
	$(LIVE_COMPOSE) stop --timeout=60

.PHONY: cat-local
cat-local:
	@echo "$(LOCAL_COMPOSE)"

.PHONY: cat-live
cat-live:
	@echo "$(LIVE_COMPOSE)"

$(DOWNLOAD_CACHE)/libsaxonhe-java_9.9.0.2+dfsg-1_all.deb:
	mkdir -p $(DOWNLOAD_CACHE)
	cd $(DOWNLOAD_CACHE) && wget http://ftp.us.debian.org/debian/pool/main/s/saxonhe/libsaxonhe-java_9.9.0.2+dfsg-1_all.deb

$(DOWNLOAD_CACHE)/libdom4j-java_2.1.1-2_all.deb:
	mkdir -p $(DOWNLOAD_CACHE)
	cd $(DOWNLOAD_CACHE) && wget http://ftp.us.debian.org/debian/pool/main/d/dom4j/libdom4j-java_2.1.1-2_all.deb

$(DOWNLOAD_CACHE)/eXist-db-setup-4.7.0.jar:
	mkdir -p $(DOWNLOAD_CACHE)
	cd $(DOWNLOAD_CACHE) && wget https://bintray.com/existdb/releases/download_file?file_path=eXist-db-setup-4.7.0.jar -O $(notdir $@)

$(CONTEXT_DOWNLOAD_CACHE)/%: $(DOWNLOAD_CACHE)/%
	-mkdir $(dir $@)
	cp -p $< $@
