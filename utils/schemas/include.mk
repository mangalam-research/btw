define UTIL_SCHEMAS_TEMPLATE
$(1)_include_mk_DIR=$(2)
$(1)_outdir=$$($(1)_include_mk_DIR)/out

$(1)_SALVE_ROOT=~/src/git-repos/salve/
$(1)_SIMPLIFY=salve-simplify
$(1)_RNG_TO_JS=$$($(1)_SALVE_ROOT)/lib/salve/rng-to-js.xsl

$$($(1)_outdir)/btw-storage.rng: $$($(1)_include_mk_DIR)/btw-storage.xml
	roma --xsl=/usr/share/xml/tei/stylesheet --noxsd --nodtd $$< $$($(1)_outdir)

$$($(1)_outdir)/btw-storage-simplified.rng: $$($(1)_outdir)/btw-storage.rng
	$$($(1)_SIMPLIFY) $$< $$@

$$($(1)_outdir)/btw-storage.js: $$($(1)_outdir)/btw-storage-simplified.rng
	xsltproc $$($(1)_RNG_TO_JS) $$< > $$@

clean:
	rm -rf $$($(1)_outdir)
endef # UTIL_SCHEMAS_TEMPLATE

$(eval $(call UTIL_SCHEMAS_TEMPLATE,UTIL_SCHEMAS_TEMPLATE,$(patsubst %/,%,$(or $(dir $(lastword $(MAKEFILE_LIST))),.))))
