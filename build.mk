-include local.mk

#
# Customizable variables. Set them in a local.mk file rather than
# modify this file. What follows are the default values.
#

# rst2html command.
RST2HTML?=rst2html

# jsdoc3 command
JSDOC3?=jsdoc

# wget command.
WGET?=wget

# Parameters to pass to behave
BEHAVE_PARAMS?=

# Whether to save the test results produced by behave.
#
# BEHAVE_SAVE?=
#
# *If not otherwise specified*, it is set to an empty string if the
# makefile is invoked in a "build system" like Buildbot or Jenkins. It
# is otherwise set to 1.
#

# The TEI hierarchy to use. This is the default location on
# Debian-type systems.
TEI?=/usr/share/xml/tei/stylesheet

# The schematron stylesheet. We rely on the TEI one since we already
# depend on TEI being present.
SCHEMATRON_TO_XSL?=/usr/share/xml/tei/odd/Utilities/iso_svrl_for_xslt2.xsl


#
# Whether or not to include in the final build the optimized version
# of wed.
#
WED_OPTIMIZED?=1

PYTHON_PARAMS?=
PYTHON?=python

#
# End of customizable variables.
#

DJANGO_MANAGE:=$(PYTHON) $(PYTHON_PARAMS) ./manage.py

WGET:=$(WGET) --no-use-server-timestamps

BUILD_DIR:=build

# This cannot be the same URL as in wed. We want to the *source*
# version of Bootstrap, not the distribution version which does not
# contain the less files.
BOOTSTRAP_URL:=https://github.com/twbs/bootstrap/archive/v3.3.7.zip
BOOTSTRAP_BASE:=bootstrap-3.3.7.zip

BOOTSTRAP_TREEVIEW_URL:=https://github.com/jonmiles/bootstrap-treeview/archive/v1.2.0.zip
BOOTSTRAP_TREEVIEW_BASE:=bootstrap-treeview-$(patsubst v%,%,$(notdir $(BOOTSTRAP_TREEVIEW_URL)))

JQUERY_COOKIE_URL:=https://github.com/carhartl/jquery-cookie/archive/v1.3.1.zip
# This creates a file name that a) identifies what it is an b) happens
# to correspond to the top directory of the zip that github creates.
JQUERY_COOKIE_BASE:=jquery-cookie-$(patsubst v%,%,$(notdir $(JQUERY_COOKIE_URL)))

DATATABLES_URL:=http://datatables.net/releases/DataTables-1.10.10.zip
# This creates a file name that a) identifies what it is an b) happens
# to correspond to the top directory of the zip that github creates.
DATATABLES_BASE:=$(notdir $(DATATABLES_URL))

DATATABLES_PLUGINS_URL:=https://github.com/DataTables/Plugins/archive/master.zip
DATATABLES_PLUGINS_BASE:=DataTables-plugins.zip

XEDITABLE_URL:=http://vitalets.github.io/x-editable/assets/zip/bootstrap3-editable-1.5.1.zip
XEDITABLE_BASE:=$(notdir $(XEDITABLE_URL))

# We don't use this yet.
#CITEPROC_URL=https://bitbucket.org/fbennett/citeproc-js/get/1.0.478.tar.bz2
#CITEPROC_BASE=citeproc-$(notdir $(CITEPROC_URL))

JQUERY_GROWL_URL:=https://github.com/ksylvest/jquery-growl/archive/v1.2.3.zip
JQUERY_GROWL_BASE:=jquery-growl-$(notdir $(JQUERY_GROWL_URL))

WED_PATH:=$(PWD)/node_modules/wed
WED_BUILD:=$(WED_PATH)/standalone$(and $(WED_OPTIMIZED),-optimized)
WED_XML_TO_HTML_PATH:=$(WED_BUILD)/lib/wed/xml-to-html.xsl
WED_HTML_TO_XML_PATH:=$(WED_BUILD)/lib/wed/html-to-xml.xsl
WED_LESS_INC_PATH:=$(WED_BUILD)/lib/wed/less-inc/

ifeq ($(wildcard $(WED_BUILD)),)
$(error Cannot find the wed build at $(WED_BUILD))
endif

# Whether we are running in a builder like Jenkins or Buildbot.
# Normalized to the value 1 when true or empty string when false.
# JENKINS_HOME is set by Jenkins. Our buildbot setup must be
# configured to set BUILDBOT.
BUILD_ENV:=$(and $(or $(JENKINS_HOME),$(BUILDBOT)),1)
BEHAVE_SAVE?=$(if $(BUILD_ENV),,1)

# When we do builds through an automated system like Buildbot, the
# builds must always happen with an optimized wed. We could override
# WED_OPTIMIZED when we detect that we are in such environment but we
# probably want to be reminded that we have been operating with an
# unoptimized wed all this time.
ifneq ($(and $(BUILD_ENV),$(if $(WED_OPTIMIZED),,1)),)
$(error You must set WED_OPTIMIZED to build with an optimized wed.)
endif

SOURCES:=$(shell find static-src -type f)
BUILD_DEST:=$(BUILD_DIR)/static-build
EXPANDED_DEST:=$(BUILD_DIR)/expanded
EXPANDED_VERSIONED_BOOTSTRAP:=$(EXPANDED_DEST)/$(BOOTSTRAP_BASE:.zip=)
EXPANDED_BOOTSTRAP:=$(EXPANDED_DEST)/bootstrap
BUILD_CONFIG:=$(BUILD_DIR)/config
LOCAL_SOURCES:=$(foreach f,$(SOURCES),$(patsubst %.less,%.css,$(patsubst static-src/%,$(BUILD_DEST)/%,$f)))
# Local sources that need to be process by specialized recipes.
GENERATED_LOCAL_SOURCES:=$(filter %.css,$(LOCAL_SOURCES)) $(BUILD_DEST)/config/requirejs-config-dev.js
# Local sources that are merely copied.
COPIED_LOCAL_SOURCES:=$(filter-out $(GENERATED_LOCAL_SOURCES),$(LOCAL_SOURCES))
BUILD_SCRIPTS:=build/scripts/

EXTERNAL:=$(BUILD_DEST)/lib/external
externalize=$(foreach f,$1,$(EXTERNAL)/$f)

# Function for automatically adding a map when the map is derived by
# adding .map to the name of the .js file.
and_map=$1 $1.map

# Function for automatically adding a map when the .js is replaced by .map.
map=$1 $(patsubst %.js,%.map,$1)

DATATABLES_PLUGIN_TARGETS:=datatables/js/dataTables.bootstrap.js datatables/css/dataTables.bootstrap.css
FINAL_SOURCES:=$(LOCAL_SOURCES) $(call externalize, jquery.cookie.js datatables bootstrap3-editable jquery-growl/js/jquery.growl.js jquery-growl/css/jquery.growl.css $(DATATABLES_PLUGIN_TARGETS) bluebird.min.js bootstrap-datepicker moment.js velocity/velocity.min.js velocity/velocity.js velocity/velocity.ui.min.js velocity/velocity.ui.js $(call and_map,last-resort.js) bluejax.js bluejax.try.js lucene-query-parser.js bootstrap-treeview.min.js bootstrap-treeview.min.css $(call map,backbone-min.js) backbone.js $(call and_map,backbone.marionette.min.js) backbone.marionette.js backbone-forms/backbone-forms.js backbone-forms/bootstrap3.js backbone-forms/bootstrap3.css $(call map,underscore-min.js) backbone.paginator.js handlebars.js handlebars.min.js backbone-relational.js backbone.radio.js $(call and_map,backbone.radio.min.js) jquery.twbsPagination.js dragula.min.js dragula.min.css ResizeObserver.js)


DERIVED_SOURCES:=$(BUILD_DEST)/lib/btw/btw-storage.js $(BUILD_DEST)/lib/btw/btw-storage-metadata.json $(BUILD_DEST)/lib/btw/btw-storage-doc

WED_FILES:=$(shell find $(WED_BUILD) -type f)
FINAL_WED_FILES:=$(foreach f,$(WED_FILES),$(patsubst $(WED_BUILD)/%,$(BUILD_DEST)/%,$f))

TEST_DATA_FILES:=$(foreach f,prepared_published_prasada.xml,build/test-data/$f)

.DELETE_ON_ERROR:

TARGETS:= javascript python-generation btw-schema-targets
.PHONY: all
all: _all
# Check we are using the same version of bootstrap in both places, we
# check against the non-optimized version because the optimized
# version is modified during optimization. We cannot include this
# check in the $(EXPANDED_BOOTSTRAP)/% rule because the recipe for
# that rule is executed only if we download a new bootstrap.
	@diff $(EXPANDED_BOOTSTRAP)/dist/css/bootstrap.css \
	  $(WED_PATH)/standalone/lib/external/bootstrap/css/bootstrap.css || \
	  { echo "There appear to be a difference between the \
	  bootstrap downloaded by BTW and the one in wed." && exit 1; }
#
	$(DJANGO_MANAGE) collectstatic --noinput




include $(shell find . -name "include.mk")

.PHONY: _all
_all: $(TARGETS) build-config build-scripts

.PHONY: python-generation
python-generation: build/python/semantic_fields/field.py

build/python/semantic_fields/field.py: semantic_fields/field.ebnf
	-mkdir -p $(dir $@)
	grako $< -o $@

.PHONY: javascript
javascript: $(FINAL_WED_FILES) $(FINAL_SOURCES) $(DERIVED_SOURCES)

$(FINAL_WED_FILES): $(BUILD_DEST)/%: $(WED_BUILD)/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage.js: utils/schemas/out/btw-storage-latest.js
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage-metadata.json: utils/schemas/out/btw-storage-metadata-latest.json
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage-doc: utils/schemas/out/btw-storage-doc-latest
	rm -rf $@
	cp -rp $< $@


$(COPIED_LOCAL_SOURCES): $(BUILD_DEST)/%: static-src/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/config/requirejs-config-dev.js: static-src/config/make-optimized-config static-src/config/requirejs-config-dev.js
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
ifneq ($(WED_OPTIMIZED),)
# This is an ad hoc way of modifying the configuration for the sake of
# an optimized build. This basically exports all the modules that are
# going to be needed from outside the bundle that contains wed.
	$< $(word 2,$^) > $@
else
	cp $(word 2,$^) $@
endif

btw-mode.css_CSS_DEPS=bibliography/static/stylesheets/bibsearch.less $(WED_LESS_INC_PATH)/*.less
btw-view.css_CSS_DEPS=static-src/lib/btw/btw-mode.less $(EXPANDED_BOOTSTRAP)/less/variables.less

.SECONDEXPANSION:
$(filter %.css,$(LOCAL_SOURCES)): $(BUILD_DEST)/%.css: static-src/%.less $$($$(notdir $$@)_CSS_DEPS)
	node_modules/.bin/lessc --include-path=$(WED_LESS_INC_PATH) $< $@

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
selenium-test: selenium_test

.PHONY: selenium_test/%.feature selenium_test
selenium_test/*.feature selenium_test: build-config $(TARGETS)
	behave $(BEHAVE_PARAMS) -D check_selenium_config=1 $@
	$(MAKE) -f build.mk all
ifneq ($(strip $(BEHAVE_SAVE)),)
	(STAMP=$$(date -Iseconds); \
	behave $(BEHAVE_PARAMS) -f plain -o test_logs/$$STAMP.log -f pretty $@ ;\
	ln -s -f $$STAMP.log test_logs/LATEST)
else
	behave $(BEHAVE_PARAMS) $@
endif # BEHAVE_SAVE

.PHONY: test
test: test-django test-karma

.PHONY: test-django
# The dependency on $(TARGETS) is needed because the tests depend on a
# complete application to run properly.
test-django: test-django-menu $(TARGETS)
	$(DJANGO_MANAGE) test --attr='!isolation'

.PHONY: test-django-menu
# The dependency on $(TARGETS) is needed because the tests depend on a
# complete application to run properly.
test-django-menu: $(TARGETS)
	$(DJANGO_MANAGE) test --attr=isolation=menu

.PHONY: test-data
test-data: $(TEST_DATA_FILES)

build/test-data/prepared_published_prasada.xml: utils/schemas/prasada.xml
	mkdir -p $(dir $@)
	$(DJANGO_MANAGE) lexicography prepare-article $< $@ $(@:.xml=.json)

.PHONY: test-karma test-data
test-karma: all
	xvfb-run ./node_modules/.bin/karma start --single-run

.PHONY: keep-latest
keep-latest:
	find test_logs -type f -not -name $$(realpath --relative-to=test_logs test_logs/LATEST) -delete

build-scripts:
	mkdir -p $(BUILD_SCRIPTS)
	$(DJANGO_MANAGE) btw generate-scripts $(BUILD_SCRIPTS)

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

$(EXPANDED_DEST):
	-mkdir $@

$(EXPANDED_BOOTSTRAP)/%:: downloads/$(BOOTSTRAP_BASE) | $(EXPANDED_DEST)
	unzip -o -DD -d $(EXPANDED_DEST) $<
	(cd $(EXPANDED_DEST); ln -sfn $(notdir $(EXPANDED_VERSIONED_BOOTSTRAP)) $(notdir $(EXPANDED_BOOTSTRAP)))

$(EXTERNAL)/jquery.cookie.js: downloads/$(JQUERY_COOKIE_BASE)
	unzip -j -o -d $(dir $@) $< $(patsubst %.zip,%,$(JQUERY_COOKIE_BASE))/$(notdir $@)
	touch $@

$(EXTERNAL)/datatables: downloads/$(DATATABLES_BASE)
	rm -rf $@/*
	mkdir -p $@/temp
	unzip -o -d $@/temp $<
	mv $@/temp/DataTables*/media/* $@
	(cd $@; rm -rf src unit_testing)
	rm -rf $@/temp

$(DATATABLES_PLUGIN_TARGETS): COMMON_DIR:=$(EXTERNAL)/datatables
$(DATATABLES_PLUGIN_TARGETS): downloads/$(DATATABLES_PLUGINS_BASE) $(EXTERNAL)/datatables
	rm -rf $(COMMON_DIR)/Plugins-master
	unzip -o -d $(COMMON_DIR) $< Plugins-master/integration/bootstrap/*
	cp $(COMMON_DIR)/Plugins-master/integration/bootstrap/3/*.js $(COMMON_DIR)/js
	cp $(COMMON_DIR)/Plugins-master/integration/bootstrap/3/*.css $(COMMON_DIR)/css
# mv $(COMMON_DIR)/Plugins-master/integration/bootstrap/images/* $(COMMON_DIR)/images
	rm -rf $(COMMON_DIR)/Plugins-master

$(EXTERNAL)/bootstrap3-editable: downloads/$(XEDITABLE_BASE)
	rm -rf $@
	unzip -o -d $(dir $@) $< $(notdir $@)/*
	touch $@

$(EXTERNAL)/bluebird%: node_modules/bluebird/js/browser/bluebird%
	cp $< $@

$(EXTERNAL)/bluejax.js: node_modules/bluejax/index.js
	cp $< $@

$(EXTERNAL)/bluejax.try.js: node_modules/bluejax.try/index.js
	cp $< $@

$(EXTERNAL)/last-resort.js%: node_modules/last-resort/dist/last-resort.min.js%
	cp $< $@

$(EXTERNAL)/bootstrap-datepicker: node_modules/bootstrap-datepicker/dist
	cp -rp $< $@

$(EXTERNAL)/moment.js: node_modules/moment/moment.js
	cp -rp $< $@

$(EXTERNAL)/lucene-query-parser.js: node_modules/lucene-query-parser/lib/lucene-query-parser.js
	cp -rp $< $@

$(EXTERNAL)/velocity/%: node_modules/velocity-animate/%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/jquery-growl/%: COMMON_DIR:=$(EXTERNAL)/jquery-growl
$(EXTERNAL)/jquery-growl/%: downloads/$(JQUERY_GROWL_BASE)
	rm -rf $(COMMON_DIR)
	unzip -o -d $(COMMON_DIR) $<
	mkdir $(COMMON_DIR)/js
	mv $(COMMON_DIR)/jquery-growl-*/javascripts/jquery.growl.js $(COMMON_DIR)/js
	mkdir $(COMMON_DIR)/css
	mv $(COMMON_DIR)/jquery-growl-*/stylesheets/jquery.growl.css $(COMMON_DIR)/css
	rm -rf $(COMMON_DIR)/jquery-growl-*
	touch $(COMMON_DIR)/js/* $(COMMON_DIR)/css/*

$(EXTERNAL)/bootstrap-treeview.%: UNZIPPED:=downloads/$(BOOTSTRAP_TREEVIEW_BASE:.zip=)
$(EXTERNAL)/bootstrap-treeview.%: downloads/$(BOOTSTRAP_TREEVIEW_BASE)
	unzip -o -d downloads $<
	cp $(UNZIPPED)/dist/* $(EXTERNAL)
	rm -rf $(UNZIPPED)

$(EXTERNAL)/backbone%: node_modules/backbone/backbone%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/backbone.marionette.%: node_modules/backbone.marionette/lib/backbone.marionette.%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/backbone.paginator.%: node_modules/backbone.paginator/lib/backbone.paginator.%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/backbone-relational%: node_modules/backbone-relational/backbone-relational%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/backbone.radio%: node_modules/backbone.marionette/node_modules/backbone.radio/build/backbone.radio%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/backbone-forms/backbone-forms.js: node_modules/backbone-forms/distribution.amd/backbone-forms.js
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/backbone-forms/bootstrap3.%: node_modules/backbone-forms/distribution.amd/templates/bootstrap3.%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/underscore%: node_modules/underscore/underscore%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/handlebars%: node_modules/handlebars/dist/handlebars%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/jquery.twbsPagination%: node_modules/twbs-pagination/jquery.twbsPagination%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/dragula%: node_modules/dragula/dist/dragula%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/ResizeObserver%: node_modules/resize-observer-polyfill/dist/ResizeObserver%
	-mkdir -p $(dir $@)
	cp -rp $< $@

downloads build:
	mkdir $@

downloads/$(JQUERY_COOKIE_BASE): | downloads
	$(WGET) -O $@ $(JQUERY_COOKIE_URL)

#downloads/$(CITEPROC_BASE): downloads
#	$(WGET) -O $@ $(CITEPROC_URL)

downloads/$(DATATABLES_BASE): | downloads
	$(WGET) -O $@ $(DATATABLES_URL)

downloads/$(DATATABLES_PLUGINS_BASE): | downloads
	$(WGET) -O $@ $(DATATABLES_PLUGINS_URL)

downloads/$(XEDITABLE_BASE): | downloads
	$(WGET) -O $@ $(XEDITABLE_URL)

downloads/$(JQUERY_GROWL_BASE): | downloads
	$(WGET) -O $@ $(JQUERY_GROWL_URL)

downloads/$(BOOTSTRAP_BASE): | downloads
	$(WGET) -O $@ '$(BOOTSTRAP_URL)'

# We do not install the npm due to the nonsensical decision that the dev
# has made to include dev dependencies among the regular dependencies.
downloads/$(BOOTSTRAP_TREEVIEW_BASE): | downloads
	$(WGET) -O $@ '$(BOOTSTRAP_TREEVIEW_URL)'

.PHONY: venv
venv:
	[ -e .btw-venv ] || virtualenv .btw-venv

.PHONY: dev-venv
dev-venv: venv
	.btw-venv/bin/pip install -r requirements.txt

.PHONY: clean
clean::
	-rm -rf build
	-rm -rf sitestatic
