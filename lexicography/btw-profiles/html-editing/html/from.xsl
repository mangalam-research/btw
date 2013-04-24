<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet 
    xmlns="http://www.tei-c.org/ns/1.0"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:btw="http://lddubeau.com/ns/btw-storage"
    exclude-result-prefixes="html"
    version="2.0">

  <xsl:namespace-alias stylesheet-prefix="tei" result-prefix="#default"/> 

  <xsl:output method="xml" indent="no"/>

  <xsl:template match="/">
    <xsl:apply-templates select="*"/>
  </xsl:template>

  <xsl:template match="*[contains(@class, '_phantom')]">
    <!-- Go straight to the children. -->
    <xsl:apply-templates select="*"/>
  </xsl:template>
  
  <xsl:template match="*">
    <xsl:element name="{tokenize(@class, '\s+')[2]}">
      <xsl:namespace name="btw" select="'http://lddubeau.com/ns/btw-storage'"/>
      <xsl:namespace name="" select="'http://www.tei-c.org/ns/1.0'"/>
      <xsl:for-each select="*[contains(@class, '_attr')]">
	<xsl:attribute name="{tokenize(@class, '\s+')[2]}" select="text()"/>
      </xsl:for-each>
      <xsl:apply-templates select="*[not(contains(@class, '_attr'))] | text()"/>
    </xsl:element>
  </xsl:template>

  <xsl:template match="text()">
    <xsl:copy-of select="."/>
  </xsl:template>
</xsl:stylesheet>
