define UTIL_SCHEMAS_TEMPLATE
$(1)_include_mk_DIR=$(2)
$(1)_outdir=$$($(1)_include_mk_DIR)/out

# Top of tei hierarchy
$(1)_TEI?=$(TEI)
$(1)_CONVERT?=$(WED_PATH)/node_modules/.bin/salve-convert
$(1)_ODD2HTML?=$$($(1)_TEI)/odds/odd2html.xsl
$(1)_SAXON?=saxon
$(1)_ROMA?=roma

#
# This funky path:
#
# $$($(1)_outdir)/utils/schemas/btw-storage.xml.compiled
#
# is due to a bug in roma. (https://github.com/TEIC/Roma/pull/2)
#
$$($(1)_outdir)/btw-storage.rng: $$($(1)_include_mk_DIR)/btw-storage.xml
	$$($(1)_ROMA) --xsl=/usr/share/xml/tei/stylesheet --dochtml --noxsd --nodtd \
		$$< $$($(1)_outdir)

$$($(1)_outdir)/utils/schemas/btw-storage.xml.compiled: $$($(1)_include_mk_DIR)/btw-storage.xml
	$$($(1)_ROMA) --xsl=/usr/share/xml/tei/stylesheet --compile \
		$$< $$($(1)_outdir)

$$($(1)_outdir)/btw-storage.json: $$($(1)_outdir)/utils/schemas/btw-storage.xml.compiled
	$$($(1)_SAXON) -xsl:/usr/share/xml/tei/stylesheet/odds/odd2json.xsl -s:$$< -o:$$@ callback=''

$$($(1)_outdir)/btw-storage-metadata.json: $$($(1)_outdir)/btw-storage.json $$($(1)_outdir)/btw-storage-doc
	$(WED_PATH)/bin/tei-to-generic-meta-json \
		--dochtml "../../../btw/btw-storage-doc/" \
		--ns tei=http://www.tei-c.org/ns/1.0 \
	        --ns btw=http://mangalamresearch.org/ns/btw-storage \
		$$< $$@


$$($(1)_outdir)/btw-storage.js: $$($(1)_outdir)/btw-storage.rng
	$$($(1)_CONVERT) $$($(1)_RNG_TO_JS) $$< $$@

$$($(1)_outdir)/btw-storage-doc: $$($(1)_outdir)/utils/schemas/btw-storage.xml.compiled
	-rm -rf $$@
	-mkdir $$@
	$$($(1)_SAXON) -s:$$< -xsl:$$($(1)_ODD2HTML) STDOUT=false splitLevel=0 outputDir=$$@

clean::
	rm -rf $$($(1)_outdir)
endef # UTIL_SCHEMAS_TEMPLATE

$(eval $(call UTIL_SCHEMAS_TEMPLATE,UTIL_SCHEMAS_TEMPLATE,$(patsubst %/,%,$(or $(dir $(lastword $(MAKEFILE_LIST))),.))))
