DEV=0
WED_PATH=$(HOME)/src/git-repos/wed

# Which wed build to use
WED_BUILD:=$(WED_PATH)/build/standalone
WED_XML_TO_HTML_PATH=$(WED_BUILD)/lib/wed/xml-to-html.xsl
WED_HTML_TO_XML_PATH=$(WED_BUILD)/lib/wed/html-to-xml.xsl

ifeq ($(wildcard $(WED_BUILD)),)
$(error Cannot find the wed build at $(WED_BUILD))
endif

SOURCES:=$(shell find static-src -type f)
FINAL_SOURCES:=$(foreach f,$(SOURCES),$(patsubst %.less,%.css,$(patsubst static-src/%,static/%,$f)))

DERIVED_SOURCES:=static/lib/btw/btw-storage.js

WED_FILES:=$(shell find $(WED_BUILD) -type f)
FINAL_WED_FILES:=$(foreach f,$(WED_FILES),$(patsubst $(WED_BUILD)/%,static/%,$f))

.DELETE_ON_ERROR:


TARGETS:= javascript
.PHONY: all
all: _all

include $(shell find . -name "include.mk")

.PHONY: _all
_all: $(TARGETS)

.PHONY: javascript
javascript: $(FINAL_WED_FILES) $(FINAL_SOURCES) $(DERIVED_SOURCES)

$(FINAL_WED_FILES): static/%: $(WED_BUILD)/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

static/lib/btw/btw-storage.js: utils/schemas/out/btw-storage.js
	cp $< $@

$(filter-out %.css,$(FINAL_SOURCES)): static/%: static-src/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(filter %.css,$(FINAL_SOURCES)): static/%.css: static-src/%.less
	lessc $< $@
