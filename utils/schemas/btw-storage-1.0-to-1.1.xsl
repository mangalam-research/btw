<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet
    xmlns="http://www.tei-c.org/ns/1.0"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:btw="http://mangalamresearch.org/ns/btw-storage"
    exclude-result-prefixes="tei"
    version="1.0">

  <xsl:preserve-space  elements="*"/>

  <xsl:output method="xml" indent="no"/>
  <xsl:param name="expected-version" select="'1.0'"/>
  <xsl:param name="new-version" select="'1.1'"/>

  <!-- Upgrade the version number. -->
  <xsl:template match="btw:entry/@version">
    <xsl:if test='string() != $expected-version'>
      <xsl:message terminate="yes">The input XML has version <xsl:value-of select="string()"/> rather than version <xsl:value-of select="$expected-version"/>.</xsl:message>
    </xsl:if>
    <xsl:attribute name="version">1.1</xsl:attribute>
  </xsl:template>

  <!-- Don't copy this. -->
  <xsl:template match="btw:english-rendition/btw:semantic-fields"/>

  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
