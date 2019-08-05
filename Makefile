#
# The make system is divided in two pieces: this file and
# build.mk. Doing it this way enables us to *force* a dependency
# recalculation every time make is run. (.PHONY by itself in a single
# Makefile does not work because the dependencies are not *reread*
# immediately. Does not work, period. Yes, we've tried.)
#

export
PASS_THROUGH:= all test test-django test-django-menu test-django-btwredis test-karma selenium-test doc python-doc keep-latest venv dev-venv test-data shrinkwrap lint

.PHONY: $(PASS_THROUGH) clean

$(PASS_THROUGH):
	$(MAKE) -f build.mk $@

selenium_test/%:
	$(MAKE) -f build.mk $@

clean:
	$(MAKE) -f build.mk $@
