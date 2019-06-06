#
# Identifier for this include fragment. We use his to create local
# variables of sorts by naming out local variables $(ME)_...
#
ME:=UTIL_SCHEMAS

$(ME)_include_mk_DIR:=$(patsubst %/,%,$(or $(dir $(lastword $(MAKEFILE_LIST))),.))
$(ME)_outdir:=$($(ME)_include_mk_DIR)/out

# Top of tei hierarchy
$(ME)_TEI?=$(TEI)
$(ME)_ODD2HTML?=$($(ME)_TEI)/odds/odd2html.xsl
$(ME)_TEITOODD?=teitoodd
$(ME)_TEITORNC?=teitornc
$(ME)_TRANG?=trang
# Parameters common to all invocations of Roma.
$(ME)_LOCALSOURCE?=--localsource=$($(ME)_include_mk_DIR)/p5subset.xml
$(ME)_TEITORNC_PARAMS?=$($(ME)_LOCALSOURCE)
$(ME)_TEITOODD_PARAMS?=$($(ME)_LOCALSOURCE)

# ls -rv sorts in reverse order by version number. (Yep, ls can do this!)
$(ME)_VERSIONS:=$(shell ls -rv $($(ME)_include_mk_DIR)/btw-storage-*.xml)
$(ME)_SCH_VERSIONS:=$(shell ls -rv $($(ME)_include_mk_DIR)/btw-storage-*.sch)

# We want to produce RNG targets for all version because we at least
# want to be able to **display** old version. We need RNG for this.
$(ME)_RNG_TARGETS:=$($(ME)_VERSIONS:$($(ME)_include_mk_DIR)/%.xml=$($(ME)_outdir)/%/btw-storage.rng)
$(ME)_LATEST_RNG_TARGET:=$(firstword $($(ME)_RNG_TARGETS))

$(ME)_XSL_TARGETS:=$($(ME)_SCH_VERSIONS:$($(ME)_include_mk_DIR)/%.sch=$($(ME)_outdir)/%.xsl)
$(ME)_LATEST_XSL_TARGET:=$(firstword $($(ME)_XSL_TARGETS))

# We need only the latest for these because we only edit the latest version.
$(ME)_LATEST_METADATA_TARGET:=$($(ME)_LATEST_RNG_TARGET:.rng=-metadata.json)
$(ME)_LATEST_DOC_TARGET:=$($(ME)_LATEST_RNG_TARGET:.rng=-doc)

$(ME)_FLAT_MODS:=$($(ME)_outdir)/flat_mods/mods-3-5.xsd

.PHONY: btw-schema-targets
btw-schema-targets: $($(ME)_RNG_TARGETS) $($(ME)_LATEST_DOC_TARGET) $($(ME)_LATEST_METADATA_TARGET) $($(ME)_XSL_TARGETS) $($(ME)_FLAT_MODS)

$($(ME)_outdir)/btw-storage-latest.rng: $($(ME)_LATEST_RNG_TARGET)
$($(ME)_outdir)/btw-storage-metadata-latest.json: $($(ME)_LATEST_METADATA_TARGET)
$($(ME)_outdir)/btw-storage-doc-latest: $($(ME)_LATEST_DOC_TARGET)

$($(ME)_outdir)/btw-storage-latest.rng $($(ME)_outdir)/btw-storage-metadata-latest.json $($(ME)_outdir)/btw-storage-doc-latest $($(ME)_outdir)/btw-storage-latest.js:
	rm -rf $@
	cp -rp $< $@

$($(ME)_RNG_TARGETS): $($(ME)_outdir)/%/btw-storage.rng: $($(ME)_include_mk_DIR)/%.xml
	$($(ME)_TEITORNC) $($(ME)_TEITORNC_PARAMS) $< $(@:.rng=.rnc)
	$($(ME)_TRANG) $(@:.rng=.rnc) $@

$($(ME)_XSL_TARGETS): $($(ME)_outdir)/%.xsl: $($(ME)_include_mk_DIR)/%.sch
	$(SAXON) -s:$< -o:$@ -xsl:$(SCHEMATRON_TO_XSL) allow-foreign=true generate-fired-rule=false

.SECONDEXPANSION:
$(ME)_MAKE_COMPILED_NAME=$($(ME)_outdir)/$(1)/btw-storage.compiled
define $(ME)_MAKE_COMPILED_RULE
$$(call $(ME)_MAKE_COMPILED_NAME,$(1)): $$($(ME)_include_mk_DIR)/$(1).xml
	$($(ME)_TEITOODD) $($(ME)_TEITOODD_PARAMS) $$< $$(call $(ME)_MAKE_COMPILED_NAME,$(1))
endef # MAKE_COMPILED_RULE

$(foreach t,$($(ME)_VERSIONS),$(eval $(call $(ME)_MAKE_COMPILED_RULE,$(t:$($(ME)_include_mk_DIR)/%.xml=%))))

$($(ME)_LATEST_RNG_TARGET:.rng=.json): $($(ME)_outdir)/%/btw-storage.json: $$(call $(ME)_MAKE_COMPILED_NAME,%)
	$(SAXON) -xsl:/usr/share/xml/tei/stylesheet/odds/odd2json.xsl -s:$< -o:$@ callback=''

$($(ME)_LATEST_METADATA_TARGET): $($(ME)_outdir)/%/btw-storage-metadata.json: $($(ME)_outdir)/%/btw-storage.json $($(ME)_include_mk_DIR)/btw-storage-metadata-fragment.yml $($(ME)_outdir)/%/btw-storage-doc
	$(WED_PATH)/bin/wed-metadata --tei --merge $(word 2,$^) $< $@

$($(ME)_outdir)/%/btw-storage-doc: $$(call $(ME)_MAKE_COMPILED_NAME,%)
	-rm -rf $@
	-mkdir $@
	$(SAXON) -s:$< -xsl:$($(ME)_ODD2HTML) STDOUT=false splitLevel=0 cssFile="./tei.css" cssPrintFile="./tei-print.css" outputDir=$@
	cp -rp $($(ME)_TEI)/tei-print.css $($(ME)_TEI)/tei.css $@/

$($(ME)_FLAT_MODS): $($(ME)_include_mk_DIR)/flatten.xsl $($(ME)_include_mk_DIR)/mods-3-5.xsd
	# Saxon will create the directory.
	$(SAXON) -xsl:$< -s:$(word 2,$^) -o:$@

clean::
	rm -rf $($(ME)_outdir)
