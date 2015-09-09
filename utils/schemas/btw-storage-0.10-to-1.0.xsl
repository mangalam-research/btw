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

  <xsl:template match="btw:entry/@version">
    <xsl:attribute name="version">1.0</xsl:attribute>
  </xsl:template>

  <!-- Don't copy this. -->
  <xsl:template match="btw:entry/@authority"/>

  <xsl:template match="@*|node()">
    <xsl:copy>
      <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
