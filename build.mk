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

# Which saxon command to use. This must be a Saxon HE version that supports
# XSLT 3.
SAXON?=./utils/saxon

BEHAVE?=./selenium_test/btw-behave.py

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

PYTHON_PARAMS?=
PYTHON?=python

#
# End of customizable variables.
#

DJANGO_MANAGE:=$(PYTHON) $(PYTHON_PARAMS) ./manage.py

WGET:=$(WGET) --no-use-server-timestamps

BUILD_DIR:=build

WED_PATH:=node_modules/@wedxml/core
WED_BUILD:=build/wed-prod
WED_SASS_INC_PATH:=$(WED_BUILD)/lib/wed/sass-inc/

# Whether we are running in a builder like Jenkins or Buildbot.
# Normalized to the value 1 when true or empty string when false.
# JENKINS_HOME is set by Jenkins. Our buildbot setup must be
# configured to set BUILDBOT.
BUILD_ENV:=$(and $(or $(JENKINS_HOME),$(BUILDBOT)),1)
BEHAVE_SAVE?=$(if $(BUILD_ENV),,1)

# "direct" sources are those source that are directly built
# one-by-one. For instance, .js files that are copied, or .less files
# that are converted to .css. An example of source that is not
# "direct" is .ts files.
DIRECT_SOURCES:=$(shell find static-src -type f ! -name "*.ts")
BUILD_DEST:=$(BUILD_DIR)/static-build
BUILD_CONFIG:=$(BUILD_DIR)/config
LOCAL_SOURCES:=$(foreach f,$(DIRECT_SOURCES),$(patsubst %.scss,%.css,$(patsubst static-src/%,$(BUILD_DEST)/%,$f)))
# Local sources that need to be process by specialized recipes.
GENERATED_LOCAL_SOURCES:=$(filter %.css,$(LOCAL_SOURCES)) $(BUILD_DEST)/config/requirejs-config-dev.js
# Local sources that are merely copied.
COPIED_LOCAL_SOURCES:=$(filter-out $(GENERATED_LOCAL_SOURCES),$(LOCAL_SOURCES))
BUILD_SCRIPTS:=$(BUILD_DIR)/scripts/
BUILD_SERVICES:=$(BUILD_DIR)/services/

EXTERNAL:=$(BUILD_DEST)/lib/external
externalize=$(foreach f,$1,$(EXTERNAL)/$f)

# Function for automatically adding a map when the map is derived by
# adding .map to the name of the .js file.
and_map=$1 $1.map

# Function for automatically adding a map when the .js is replaced by .map.
map=$1 $(patsubst %.js,%.map,$1)

DATATABLES_PLUGIN_TARGETS:=$(call externalize, datatables/js/dataTables.bootstrap4.js datatables/css/dataTables.bootstrap4.css)
FINAL_SOURCES:=$(LOCAL_SOURCES) \
  $(BUILD_DEST)/lib/requirejs/require.js\
  $(BUILD_DEST)/lib/requirejs/text.js\
  $(BUILD_DEST)/lib/requirejs/json.js\
  $(call externalize, \
	datatables\
	jquery.growl/js/jquery.growl.js jquery.growl/css/jquery.growl.css\
	bluebird.min.js\
	bootstrap-datepicker\
	moment.js\
	velocity/velocity.min.js velocity/velocity.js\
	velocity/velocity.ui.min.js velocity/velocity.ui.js\
	last-resort.js\
	bluejax.js bluejax.try.js\
	lucene-query-parser.js\
	bootstrap-treeview.min.js bootstrap-treeview.min.css\
	$(call map,backbone-min.js) backbone.js\
	$(call and_map,backbone.marionette.min.js) backbone.marionette.js\
	backbone-forms/backbone-forms.js backbone-forms/bootstrap3.js backbone-forms/bootstrap3.css\
	$(call and_map,underscore-min.js)\
	backbone.paginator.js\
	handlebars.js handlebars.min.js\
	backbone-relational.js\
	backbone.radio.js $(call and_map,backbone.radio.min.js)\
	jquery.twbsPagination.js\
	dragula.min.js dragula.min.css\
	ResizeObserver.js\
	js.cookie.js\
	jquery.js\
	bootstrap/js/bootstrap.js bootstrap/css/bootstrap.min.css\
	popper.min.js\
	lodash\
	font-awesome/css/font-awesome.min.css\
	font-awesome/fonts\
	bootstrap-notify.js\
	$(call and_map,salve.min.js)\
	inversify\
	$(call and_map,interact.min.js)\
	bloodhound.min.js\
	typeahead.jquery.min.js\
	typeaheadjs.css\
	log4javascript.js\
	$(call and_map,ajv.min.js)\
	merge-options.js\
	is-plain-obj.js\
	core-js.min.js)\
	$(DATATABLES_PLUGIN_TARGETS)

DERIVED_SOURCES:=$(BUILD_DEST)/lib/btw/btw-storage.rng $(BUILD_DEST)/lib/btw/btw-storage-metadata.json $(BUILD_DEST)/lib/btw/btw-storage-doc

TEST_DATA_FILES:=$(foreach f,prepared_published_prasada.xml,build/test-data/$f)

.DELETE_ON_ERROR:

TARGETS:= javascript typescript python-generation btw-schema-targets
.PHONY: all
all: _all
# We use --clear for two reasons: a) we want old crap to be removed
# and b) there are situations where the timestamps of files installed
# with NPM can trip us. Trying to fix it as part of the Makefile is
# onerous.
	$(DJANGO_MANAGE) collectstatic --noinput --clear




include $(shell find . -name "include.mk")

.PHONY: _all
_all: $(TARGETS) build-config build-scripts

.PHONY: python-generation
python-generation: build/python/semantic_fields/field.py

build/python/semantic_fields/field.py: semantic_fields/field.ebnf
	-mkdir -p $(dir $@)
	tatsu $< -o $@

.PHONY: javascript
javascript: $(WED_BUILD) $(FINAL_SOURCES) $(DERIVED_SOURCES)

.PHONY: typescript
typescript:
	./node_modules/.bin/tsc -p static-src/lib/btw/tsconfig.json --outDir $(BUILD_DEST)/lib/btw/

$(BUILD_DIR)/wed-dev/entry.js: wed/entry.ts
	./node_modules/.bin/tsc -p wed/tsconfig.json --outDir $(dir $@)

$(WED_BUILD): $(BUILD_DIR)/wed-dev/entry.js
	./node_modules/.bin/wed-build wed/wed.config.js
	rm -rf $(BUILD_DEST)/lib/wed*
	-mkdir -p $(BUILD_DEST)/lib
	cp -rp $(WED_BUILD)/lib/wed* $(BUILD_DEST)/lib


$(BUILD_DEST)/lib/btw/btw-storage.rng: utils/schemas/out/btw-storage-latest.rng
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage-metadata.json: utils/schemas/out/btw-storage-metadata-latest.json
	cp $< $@

$(BUILD_DEST)/lib/btw/btw-storage-doc: utils/schemas/out/btw-storage-doc-latest
	rm -rf $@
	cp -rp $< $@


$(COPIED_LOCAL_SOURCES): $(BUILD_DEST)/%: static-src/%
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/config/requirejs-config-dev.js: static-src/config/requirejs-config-dev.js
	-@[ -e $(dir $@) ] || mkdir -p $(dir $@)
	cp $< $@

btw-mode.css_CSS_DEPS=bibliography/static/stylesheets/bibsearch.scss $(WED_SASS_INC_PATH)/*.scss
btw-view.css_CSS_DEPS=static-src/lib/btw/btw-mode.scss node_modules/bootstrap/scss/_variables.scss

.SECONDEXPANSION:
$(filter %.css,$(LOCAL_SOURCES)): $(BUILD_DEST)/%.css: static-src/%.scss $$(wildcard $$($$(notdir $$@)_CSS_DEPS))
	node_modules/.bin/node-sass --include-path=$(WED_SASS_INC_PATH) $< $@

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
# This should be removed when we upgrade wed and wedutil (wedutil>=0.22.1)
selenium_test/*.feature selenium_test: export WEDUTIL_SKIP_OSX_CHECK := 1
selenium_test/*.feature selenium_test: build-config $(TARGETS)
	$(BEHAVE) $(BEHAVE_PARAMS) -D check_selenium_config=1 $@
	$(MAKE) -f build.mk all
ifneq ($(strip $(BEHAVE_SAVE)),)
	(STAMP=$$(date -Iseconds); \
	$(BEHAVE) $(BEHAVE_PARAMS) -f plain -o test_logs/$$STAMP.log -f pretty $@ ;\
	ln -s -f $$STAMP.log test_logs/LATEST)
else
	$(BEHAVE) $(BEHAVE_PARAMS) $@
endif # BEHAVE_SAVE

.PHONY: test
test: test-django test-karma

.PHONY: test-django
# The dependency on $(TARGETS) is needed because the tests depend on a
# complete application to run properly.
test-django: test-django-menu test-django-btwredis $(TARGETS)
	$(DJANGO_MANAGE) test --ignore-files=test_btwredis.py --ignore-files=test_menus.py

.PHONY: test-django-menu
# The dependency on $(TARGETS) is needed because the tests depend on a
# complete application to run properly.
test-django-menu: $(TARGETS)
	$(DJANGO_MANAGE) test ./core/tests/test_menus.py

.PHONY: test-django-btwredis
test-django-btwredis:
	$(DJANGO_MANAGE) test ./btw_management/tests/test_btwredis.py

.PHONY: test-data
test-data: $(TEST_DATA_FILES)

build/test-data/prepared_published_prasada.xml: utils/schemas/prasada.xml
	mkdir -p $(dir $@)
	$(DJANGO_MANAGE) lexicography prepare-article $< $@ $(@:.xml=.json)

.PHONY: test-karma
test-karma: all test-data
	./node_modules/.bin/karma start --single-run

.PHONY: keep-latest
keep-latest:
	find test_logs -type f -not -name $$(realpath --relative-to=test_logs test_logs/LATEST) -delete

build-scripts:
	mkdir -p $(BUILD_SCRIPTS) $(BUILD_SERVICES)
	$(DJANGO_MANAGE) btw generate-scripts $(BUILD_SCRIPTS)
	$(DJANGO_MANAGE) btw generate-systemd-services $(BUILD_SCRIPTS) $(BUILD_SERVICES)

build-config: $(CONFIG_TARGETS) | $(BUILD_CONFIG)

$(BUILD_CONFIG):
	mkdir $@

# See Makefile for the flip side of this. We need to not fail
# if the file is missing so that ``make clean`` works on a new
# checkout of the code.
-include $(CONFIG_DEPS)

# Here are the actual targets that build the actual config files.
$(BUILD_CONFIG)/%:
	cp $< $@

$(BUILD_CONFIG)/nginx.conf:
	sed -e's;@PWD@;$(PWD);'g $< > $@

$(EXTERNAL)/datatables: node_modules/datatables/media
	-mkdir -p $(dir $@)
	rm -rf $@
	cp -rp node_modules/datatables/media $@

$(DATATABLES_PLUGIN_TARGETS): $(EXTERNAL)/datatables/%: node_modules/datatables.net-bs4/%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/core-js.min.js: node_modules/core-js/client/core.min.js
	-mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/lib/requirejs/require.js: node_modules/requirejs/require.js
	-mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/lib/requirejs/text.js: node_modules/requirejs-text/text.js
	-mkdir -p $(dir $@)
	cp $< $@

$(BUILD_DEST)/lib/requirejs/json.js: node_modules/requirejs-plugins/src/json.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/font-awesome/%: node_modules/font-awesome/%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/bootstrap-notify.js: node_modules/bootstrap-notify/bootstrap-notify.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/salve%: node_modules/salve/salve%
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/interact%: node_modules/interactjs/dist/interact%
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/merge-options.js: node_modules/merge-options/index.js
	-mkdir -p $(dir $@)
	echo "define(function (require, exports, module) {" > $@
	cat $< >> $@
	echo "});" >> $@

$(EXTERNAL)/is-plain-obj.js: node_modules/is-plain-obj/index.js
	-mkdir -p $(dir $@)
	echo "define(function (require, exports, module) {" > $@
	cat $< >> $@
	echo "});" >> $@

$(EXTERNAL)/bloodhound.min.js: node_modules/corejs-typeahead/dist/bloodhound.min.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/typeahead.jquery.min.js: node_modules/corejs-typeahead/dist/typeahead.jquery.min.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/typeaheadjs.css: node_modules/typeahead.js-bootstrap4-css/typeaheadjs.css
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/log4javascript.js: node_modules/log4javascript/log4javascript.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/ajv.%: node_modules/ajv/dist/ajv.%
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/inversify: node_modules/inversify/amd
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/js.cookie.js: node_modules/js-cookie/src/js.cookie.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/bluebird%: node_modules/bluebird/js/browser/bluebird%
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/bluejax.js: node_modules/bluejax/index.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/bluejax.try.js: node_modules/bluejax.try/index.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/last-resort.js: node_modules/last-resort/last-resort.js
	-mkdir -p $(dir $@)
	cp $< $@

$(EXTERNAL)/bootstrap-datepicker: node_modules/bootstrap-datepicker/dist
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/moment.js: node_modules/moment/moment.js
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/lucene-query-parser.js: node_modules/lucene-query-parser/lib/lucene-query-parser.js
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/velocity/%: node_modules/velocity-animate/%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/jquery.growl/css/jquery.growl.css: node_modules/jquery.growl/stylesheets/jquery.growl.css
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/jquery.growl/js/jquery.growl.js: node_modules/jquery.growl/javascripts/jquery.growl.js
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/jquery.js: node_modules/jquery/dist/jquery.js
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/bootstrap/js/bootstrap.js: node_modules/bootstrap/dist/js/bootstrap.js
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/popper.min.js: node_modules/popper.js/dist/umd/popper.min.js
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/bootstrap/css/bootstrap.min.css: node_modules/bootstrap/dist/css/bootstrap.min.css
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/bootstrap-treeview.%: node_modules/patternfly-bootstrap-treeview/dist/bootstrap-treeview.%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/backbone%: node_modules/backbone/backbone%
	-mkdir -p $(dir $@)
	cp -rp $< $@

$(EXTERNAL)/lodash: node_modules/lodash
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

# backbone.radio may be installed in different locations.
BACKBONE_RADIO:=$(or $(wildcard node_modules/backbone.radio),$(wildcard node_modules/backbone.marionette/node_modules/backbone.radio))
$(EXTERNAL)/backbone.radio%: $(BACKBONE_RADIO)/build/backbone.radio%
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

.PHONY: eslint
eslint:
	./node_modules/.bin/eslint *.js '{karma_tests,bibliography,lexicography,semantic_fields,wed,core,static-src}/**/*.js'

.PHONY: tslint
tslint:
	./node_modules/.bin/tslint -p static-src/lib/btw/tsconfig.json

.PHONY: lint
lint: tslint eslint

.PHONY: venv
venv:
	[ -e .btw-venv ] || python3 -m venv .btw-venv

.PHONY: dev-venv
dev-venv: venv
	.btw-venv/bin/pip install -r frozen-requirements.txt

.PHONY: shrinkwrap
shrinkwrap:
	npm prune
	npm shrinkwrap

.PHONY: freeze
freeze:
	tasks/freeze


.PHONY: clean
clean::
	-rm -rf build
	-rm -rf sitestatic
