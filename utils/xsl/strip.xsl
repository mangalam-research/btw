<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:btw="http://lddubeau.com/ns/btw-storage"
    version="1.0">

  <xsl:output method="xml" indent="no" encoding="UTF-8"
              omit-xml-declaration="yes"/>
  <xsl:strip-space elements="*"/>
  <xsl:preserve-space elements="tei:p tei:cit tei:lbl tei:quote btw:cit btw:tr"/>
  <xsl:template match="node()|@*">
    <xsl:copy>
      <xsl:apply-templates select="node()|@*"/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="comment()" priority="99">
  </xsl:template>

</xsl:stylesheet>
