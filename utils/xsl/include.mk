_include_mk_DIR=$(patsubst %/,%,$(or $(dir $(lastword $(MAKEFILE_LIST))),.))
_outdir=$(_include_mk_DIR)/out

$(_outdir):
	@mkdir -p $@

$(_outdir)/xml-to-html.xsl: $(_include_mk_DIR)/xml-to-html.xsl.in | $(_outdir)
	sed -e's;@WED_XML_TO_HTML_PATH@;$(WED_XML_TO_HTML_PATH);' $< > $@

$(_outdir)/html-to-xml.xsl: $(WED_HTML_TO_XML_PATH) | $(_outdir)
	cp $< $@

TARGETS += $(_outdir)/xml-to-html.xsl $(_outdir)/html-to-xml.xsl
