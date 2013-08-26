WED_PATH=$(HOME)/src/git-repos/wed

# rst2html command.
RST2HTML?=rst2html

# Which wed build to use
WED_BUILD:=$(WED_PATH)/build/standalone
WED_XML_TO_HTML_PATH=$(WED_BUILD)/lib/wed/xml-to-html.xsl
WED_HTML_TO_XML_PATH=$(WED_BUILD)/lib/wed/html-to-xml.xsl

ifeq ($(wildcard $(WED_BUILD)),)
$(error Cannot find the wed build at $(WED_BUILD))
endif

SOURCES:=$(shell find static-src -type f)
BUILD_DEST:=static-build
FINAL_SOURCES:=$(foreach f,$(SOURCES),$(patsubst %.less,%.css,$(patsubst static-src/%,$(BUILD_DEST)/%,$f)))

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

$(filter-out %.css,$(FINAL_SOURCES)): $(BUILD_DEST)/%: static-src/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(filter %.css,$(FINAL_SOURCES)): $(BUILD_DEST)/%.css: static-src/%.less
	lessc $< $@

doc: README.html
	(cd doc; make html)

README.html: README.rst
	$(RST2HTML) $< $@
