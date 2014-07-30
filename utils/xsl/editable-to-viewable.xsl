<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:internal="internal"
    exclude-result-prefixes="xs"
    version="2.0">

  <xsl:preserve-space  elements="*"/>

  <xsl:output method="xhtml" indent="no" omit-xml-declaration="yes"/>

  <xsl:template match="node()|@*">
    <xsl:copy>
      <xsl:apply-templates select="node()|@*"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
