define UTIL_SCHEMAS_TEMPLATE
$(1)_include_mk_DIR=$(2)
$(1)_outdir=$$($(1)_include_mk_DIR)/out

$(1)_CONVERT=salve-convert

$$($(1)_outdir)/btw-storage.rng: $$($(1)_include_mk_DIR)/btw-storage.xml
	roma --xsl=/usr/share/xml/tei/stylesheet --noxsd --nodtd $$< $$($(1)_outdir)

$$($(1)_outdir)/btw-storage.js: $$($(1)_outdir)/btw-storage.rng
	$$($(1)_CONVERT) $$($(1)_RNG_TO_JS) $$< $$@

clean:
	rm -rf $$($(1)_outdir)
endef # UTIL_SCHEMAS_TEMPLATE

$(eval $(call UTIL_SCHEMAS_TEMPLATE,UTIL_SCHEMAS_TEMPLATE,$(patsubst %/,%,$(or $(dir $(lastword $(MAKEFILE_LIST))),.))))
