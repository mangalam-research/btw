-include local.mk

#
# Customizable variables. Set them in a local.mk file rather than
# modify this file. What follows are the default values.
#

# No default value for wed path
ifndef WED_PATH
$(error WED_PATH must point to the top level directory of wed\'s file tree.)
endif

# rst2html command.
RST2HTML?=rst2html

# jsdoc3 command
JSDOC3?=jsdoc

# wget command.
WGET?=wget

# Parameters to pass to behave
BEHAVE_PARAMS?=

# The TEI hierarchy to use. This is the default location on
# Debian-type systems.
TEI?=/usr/share/xml/tei/stylesheet

#
# End of customizable variables.
#

WGET:=$(WGET) --no-use-server-timestamps

BUILD_DIR:=build

QUNIT_VERSION:=1.12.0

JQUERY_COOKIE_URL:=https://github.com/carhartl/jquery-cookie/archive/v1.3.1.zip
# This creates a file name that a) identifies what it is an b) happens
# to correspond to the top directory of the zip that github creates.
JQUERY_COOKIE_BASE:=jquery-cookie-$(patsubst v%,%,$(notdir $(JQUERY_COOKIE_URL)))

DATATABLES_URL:=http://datatables.net/releases/DataTables-1.9.4.zip
# This creates a file name that a) identifies what it is an b) happens
# to correspond to the top directory of the zip that github creates.
DATATABLES_BASE:=$(notdir $(DATATABLES_URL))


# We don't use this yet.
#CITEPROC_URL=https://bitbucket.org/fbennett/citeproc-js/get/1.0.478.tar.bz2
#CITEPROC_BASE=citeproc-$(notdir $(CITEPROC_URL))

# Which wed build to use
WED_BUILD:=$(WED_PATH)/build/standalone
WED_XML_TO_HTML_PATH:=$(WED_BUILD)/lib/wed/xml-to-html.xsl
WED_HTML_TO_XML_PATH:=$(WED_BUILD)/lib/wed/html-to-xml.xsl

ifeq ($(wildcard $(WED_BUILD)),)
$(error Cannot find the wed build at $(WED_BUILD))
endif


SOURCES:=$(shell find static-src -type f)
BUILD_DEST:=$(BUILD_DIR)/static-build
BUILD_CONFIG:=$(BUILD_DIR)/config
LOCAL_SOURCES:=$(foreach f,$(SOURCES),$(patsubst %.less,%.css,$(patsubst static-src/%,$(BUILD_DEST)/%,$f)))

FINAL_SOURCES:=$(LOCAL_SOURCES) $(BUILD_DEST)/lib/external/qunit-$(QUNIT_VERSION).js $(BUILD_DEST)/lib/external/qunit-$(QUNIT_VERSION).css $(BUILD_DEST)/lib/external/jquery.cookie.js $(BUILD_DEST)/lib/external/datatables

DERIVED_SOURCES:=$(BUILD_DEST)/lib/btw/btw-storage.js $(BUILD_DEST)/lib/btw/btw-storage-metadata.json $(BUILD_DEST)/lib/btw/btw-storage-doc

WED_FILES:=$(shell find $(WED_BUILD) -type f)
FINAL_WED_FILES:=$(foreach f,$(WED_FILES),$(patsubst $(WED_BUILD)/%,$(BUILD_DEST)/%,$f))

.DELETE_ON_ERROR:

TARGETS:= javascript
.PHONY: all
all: _all
	./manage.py collectstatic --noinput

include $(shell find . -name "include.mk")

.PHONY: _all
_all: $(TARGETS) build-config

.PHONY: javascript
javascript: $(FINAL_WED_FILES) $(FINAL_SOURCES) $(DERIVED_SOURCES)

$(FINAL_WED_FILES): $(BUILD_DEST)/%: $(WED_BUILD)/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage.js: utils/schemas/out/btw-storage.js
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage-metadata.json: utils/schemas/out/btw-storage-metadata.json
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage-doc: utils/schemas/out/btw-storage-doc
	rm -rf $@
	cp -rp $< $@


$(filter-out %.css,$(LOCAL_SOURCES)): $(BUILD_DEST)/%: static-src/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(filter %.css,$(LOCAL_SOURCES)): $(BUILD_DEST)/%.css: static-src/%.less
	lessc $< $@

APIDOC_EXCLUDE:=$(shell find $$PWD -name 'migrations' -type d)

.PHONY: python-doc
python-doc:
	sphinx-apidoc -f -o doc/_apidoc . $(APIDOC_EXCLUDE)
	(cd doc; make html)

.PHONY: doc
doc: python-doc build/doc README.html

build/doc: build $(filter %.js, $(SOURCES))
	$(JSDOC3) -p -c jsdoc.conf.json -d build/doc -r static-src

README.html: README.rst
	$(RST2HTML) $< $@

.PHONY: selenium-test
selenium-test: all
	behave $(BEHAVE_PARAMS) selenium_test

.PHONY: selenium_test/%.feature
selenium_test/%.feature: all
	behave $(BEHAVE_PARAMS) $@

build-config: $(CONFIG_TARGETS) | $(BUILD_CONFIG)

$(BUILD_CONFIG):
	mkdir $@

# See Makefile for the flip side of this.
include $(CONFIG_DEPS)

# Here are the actual targets that build the actual config files.
$(BUILD_CONFIG)/%:
	cp $< $@

$(BUILD_CONFIG)/nginx.conf:
	sed -e's;@PWD@;$(PWD);'g $< > $@

node_modules:
	-mkdir $@

node_modules/qunitjs: | node_modules
	npm install qunitjs@1.12.0

$(BUILD_DEST)/lib/external/qunit-$(QUNIT_VERSION).%: node_modules/qunitjs/qunit/qunit.% | node_modules/qunitjs
	cp $< $@

$(BUILD_DEST)/lib/external/jquery.cookie.js: downloads/$(JQUERY_COOKIE_BASE)
	unzip -j -o -d $(dir $@) $< $(patsubst %.zip,%,$(JQUERY_COOKIE_BASE))/$(notdir $@)
	touch $@

$(BUILD_DEST)/lib/external/datatables: downloads/$(DATATABLES_BASE)
	rm -rf $@/*
	mkdir -p $@/temp
	unzip -o -d $@/temp $<
	mv $@/temp/DataTables*/media/* $@
	(cd $@; rm -rf src unit_testing)
	rm -rf $@/temp

downloads build:
	mkdir $@

downloads/$(JQUERY_COOKIE_BASE): downloads
	$(WGET) -O $@ $(JQUERY_COOKIE_URL)

downloads/$(CITEPROC_BASE): downloads
	$(WGET) -O $@ $(CITEPROC_URL)

downloads/$(DATATABLES_BASE): downloads
	$(WGET) -O $@ $(DATATABLES_URL)
