WED_PATH=$(HOME)/src/git-repos/wed

# rst2html command.
RST2HTML?=rst2html

QUNIT_VERSION=1.12.0

JQUERY_COOKIE_URL=https://github.com/carhartl/jquery-cookie/archive/v1.3.1.zip
# This creates a file name that a) identifies what it is an b) happens
# to correspond to the top directory of the zip that github creates.
JQUERY_COOKIE_BASE=jquery-cookie-$(patsubst v%,%,$(notdir $(JQUERY_COOKIE_URL)))

# We don't use this yet.
#CITEPROC_URL=https://bitbucket.org/fbennett/citeproc-js/get/1.0.478.tar.bz2
#CITEPROC_BASE=citeproc-$(notdir $(CITEPROC_URL))

# Which wed build to use
WED_BUILD:=$(WED_PATH)/build/standalone
WED_XML_TO_HTML_PATH=$(WED_BUILD)/lib/wed/xml-to-html.xsl
WED_HTML_TO_XML_PATH=$(WED_BUILD)/lib/wed/html-to-xml.xsl

ifeq ($(wildcard $(WED_BUILD)),)
$(error Cannot find the wed build at $(WED_BUILD))
endif


SOURCES:=$(shell find static-src -type f)
BUILD_DEST:=static-build
LOCAL_SOURCES:=$(foreach f,$(SOURCES),$(patsubst %.less,%.css,$(patsubst static-src/%,$(BUILD_DEST)/%,$f)))

FINAL_SOURCES:=$(LOCAL_SOURCES) $(BUILD_DEST)/lib/qunit-$(QUNIT_VERSION).js $(BUILD_DEST)/lib/qunit-$(QUNIT_VERSION).css $(BUILD_DEST)/lib/jquery.cookie.js

DERIVED_SOURCES:=$(BUILD_DEST)/lib/btw/btw-storage.js

WED_FILES:=$(shell find $(WED_BUILD) -type f)
FINAL_WED_FILES:=$(foreach f,$(WED_FILES),$(patsubst $(WED_BUILD)/%,$(BUILD_DEST)/%,$f))

.DELETE_ON_ERROR:


TARGETS:= javascript
.PHONY: all
all: _all
	./manage.py collectstatic --noinput

include $(shell find . -name "include.mk")

.PHONY: _all
_all: $(TARGETS)

.PHONY: javascript
javascript: $(FINAL_WED_FILES) $(FINAL_SOURCES) $(DERIVED_SOURCES)

$(FINAL_WED_FILES): $(BUILD_DEST)/%: $(WED_BUILD)/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage.js: utils/schemas/out/btw-storage.js
	cp $< $@

$(filter-out %.css,$(LOCAL_SOURCES)): $(BUILD_DEST)/%: static-src/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(filter %.css,$(LOCAL_SOURCES)): $(BUILD_DEST)/%.css: static-src/%.less
	lessc $< $@

doc: README.html
	(cd doc; make html)

README.html: README.rst
	$(RST2HTML) $< $@

node_modules:
	-mkdir $@

node_modules/qunitjs: | node_modules
	npm install qunitjs@1.12.0

$(BUILD_DEST)/lib/qunit-$(QUNIT_VERSION).js: node_modules/qunitjs/qunit/qunit.js | node_modules/qunitjs
	cp $< $@

$(BUILD_DEST)/lib/qunit-$(QUNIT_VERSION).css: node_modules/qunitjs/qunit/qunit.css | node_modules/qunitjs
	cp $< $@

$(BUILD_DEST)/lib/jquery.cookie.js: downloads/$(JQUERY_COOKIE_BASE)
	unzip -j -o -d $(dir $@) $< $(patsubst %.zip,%,$(JQUERY_COOKIE_BASE))/$(notdir $@)
	touch $@

downloads:
	mkdir $@

downloads/$(JQUERY_COOKIE_BASE): downloads
	wget -O $@ $(JQUERY_COOKIE_URL)

downloads/$(CITEPROC_BASE): downloads
	wget -O $@ $(CITEPROC_URL)
