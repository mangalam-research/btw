#
# Identifier for this include fragment. We use his to create local
# variables of sorts by naming out local variables $(ME)_...
#
ME:=UTIL_SCHEMAS

$(ME)_include_mk_DIR=$(patsubst %/,%,$(or $(dir $(lastword $(MAKEFILE_LIST))),.))
$(ME)_outdir:=$($(ME)_include_mk_DIR)/out

# Top of tei hierarchy
$(ME)_TEI?=$(TEI)
$(ME)_CONVERT?=$(WED_PATH)/node_modules/.bin/salve-convert
$(ME)_ODD2HTML?=$($(ME)_TEI)/odds/odd2html.xsl
$(ME)_SAXON?=saxon
$(ME)_ROMA?=roma

# ls -rv sorts in reverse order by version number. (Yep, ls can do this!)
$(ME)_VERSIONS:=$(shell ls -rv $($(ME)_include_mk_DIR)/btw-storage-*.xml)

# We want to produce RNG targets for all version because we at least
# want to be able to **display** old version. We need RNG for this.
$(ME)_RNG_TARGETS:=$($(ME)_VERSIONS:$($(ME)_include_mk_DIR)/%.xml=$($(ME)_outdir)/%/btw-storage.rng)
$(ME)_LATEST_RNG_TARGET:=$(firstword $($(ME)_RNG_TARGETS))

# We need only the latest for these because we only edit the latest version.
$(ME)_LATEST_METADATA_TARGET:=$($(ME)_LATEST_RNG_TARGET:.rng=-metadata.json)
$(ME)_LATEST_DOC_TARGET:=$($(ME)_LATEST_RNG_TARGET:.rng=-doc)
$(ME)_LATEST_JS_TARGET:=$($(ME)_LATEST_RNG_TARGET:.rng=.js)

.PHONY: btw-schema-targets
btw-schema-targets: $($(ME)_RNG_TARGETS) $($(ME)_LATEST_DOC_TARGET) $($(ME)_LATEST_METADATA_TARGET) $($(ME)_LATEST_JS_TARGET)

$($(ME)_outdir)/btw-storage-latest.rng: $($(ME)_LATEST_RNG_TARGET)
$($(ME)_outdir)/btw-storage-metadata-latest.json: $($(ME)_LATEST_METADATA_TARGET)
$($(ME)_outdir)/btw-storage-doc-latest: $($(ME)_LATEST_DOC_TARGET)
$($(ME)_outdir)/btw-storage-latest.js: $($(ME)_LATEST_JS_TARGET)


$($(ME)_outdir)/btw-storage-latest.rng $($(ME)_outdir)/btw-storage-metadata-latest.json $($(ME)_outdir)/btw-storage-doc-latest $($(ME)_outdir)/btw-storage-latest.js:
	cp -rp $< $@

$($(ME)_RNG_TARGETS): $($(ME)_outdir)/%/btw-storage.rng: $($(ME)_include_mk_DIR)/%.xml
	$($(ME)_ROMA) --xsl=/usr/share/xml/tei/stylesheet --dochtml --noxsd --nodtd \
		$< $(dir $@)

#
# This funky path:
#
# $($(ME)_outdir)/utils/schemas/btw-storage.xml.compiled
#
# is due to a bug in roma. (https://github.com/TEIC/Roma/pull/2)
#
.SECONDEXPANSION:
$(ME)_MAKE_COMPILED_NAME=$($(1)_outdir)/$(2)/utils/schemas/$(2).xml.compiled
define $(ME)_MAKE_COMPILED_RULE
$$(call $(1)_MAKE_COMPILED_NAME,$(1),$(2)): $$($(1)_include_mk_DIR)/$(2).xml
	$$($(1)_ROMA) --xsl=/usr/share/xml/tei/stylesheet --compile \
		$$< $$($(1)_outdir)/$(2)
endef # MAKE_COMPILED_RULE

$(foreach t,$($(ME)_VERSIONS),$(eval $(call $(ME)_MAKE_COMPILED_RULE,$(ME),$(t:$($(ME)_include_mk_DIR)/%.xml=%))))

$($(ME)_LATEST_RNG_TARGET:.rng=.json): $($(ME)_outdir)/%/btw-storage.json: $$(call $(ME)_MAKE_COMPILED_NAME,$(ME),%)
	$($(ME)_SAXON) -xsl:/usr/share/xml/tei/stylesheet/odds/odd2json.xsl -s:$< -o:$@ callback=''

$($(ME)_LATEST_METADATA_TARGET): $($(ME)_outdir)/%/btw-storage-metadata.json: $($(ME)_outdir)/%/btw-storage.json $($(ME)_outdir)/%/btw-storage-doc
	$(WED_PATH)/bin/tei-to-generic-meta-json \
		--dochtml "../../../btw/btw-storage-doc/" \
		--ns tei=http://www.tei-c.org/ns/1.0 \
	        --ns btw=http://mangalamresearch.org/ns/btw-storage \
		$< $@


$($(ME)_outdir)/%/btw-storage.js: $($(ME)_outdir)/%/btw-storage.rng
	$($(ME)_CONVERT) $($(ME)_RNG_TO_JS) $< $@

$($(ME)_outdir)/%/btw-storage-doc: $$(call $(ME)_MAKE_COMPILED_NAME,$(ME),%)
	-rm -rf $@
	-mkdir $@
	$($(ME)_SAXON) -s:$< -xsl:$($(ME)_ODD2HTML) STDOUT=false splitLevel=0 outputDir=$@

clean::
	rm -rf $($(ME)_outdir)
