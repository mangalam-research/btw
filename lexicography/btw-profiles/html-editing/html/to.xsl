<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet 
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:btw="http://lddubeau.com/ns/btw-storage"
    xmlns:toffee="http://lddubeau.com/ns/toffee"
    exclude-result-prefixes="tei html btw toffee"
    version="2.0">

  <xsl:strip-space elements="*"/>
  <xsl:preserve-space elements="tei:p tei:cit tei:lbl tei:quote btw:cit btw:tr"/>

  <xsl:namespace-alias stylesheet-prefix="tei" result-prefix="#default"/> 

  <xsl:output method="xhtml" indent="no" omit-xml-declaration="yes"/>
  
  <xsl:template match="*" name="copy">
    <div><xsl:attribute name="class" select="concat(name(), ' _real')"/><xsl:apply-templates select="node()|@*"/></div>
  </xsl:template>

  <xsl:template match="text()">
    <xsl:copy-of select="."/>
  </xsl:template>


  <xsl:template match="@*">
    <div><xsl:attribute name="class" select="concat(name(), ' _attr')"/><xsl:value-of select="."/></div>
  </xsl:template>
</xsl:stylesheet>
