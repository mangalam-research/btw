<xsl:stylesheet version="1.0"
		xmlns="http://www.w3.org/1999/xhtml"
		xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
		xmlns:atom="http://www.w3.org/2005/Atom"
		xmlns:zapi="http://zotero.org/ns/api"
		exclude-result-prefixes="atom zapi"
		>
  <xsl:output method="xhtml"/>

  <xsl:param name="first-index"/>

  <xsl:template match="node()|@*">
    <xsl:copy>
      <xsl:apply-templates/>
    </xsl:copy>
  </xsl:template>

  <xsl:template match="atom:feed">
    <xsl:variable name="count" select="count(atom:entry)"/>
    <xsl:variable name="last-index" select="$first-index - 1 + $count"/>
    <xsl:variable name="total" select="zapi:totalResults/text()"/>
    <p>Results <xsl:value-of select="$first-index"/>-<xsl:value-of select="$last-index"/> of <xsl:value-of select="$total"/></p>
    <ul>
      <xsl:for-each select="atom:entry">
	<li>
	  <xsl:apply-templates select="current()"/>
	</li>
      </xsl:for-each>
    </ul>
  </xsl:template>

  <xsl:template match="atom:entry">
    <xsl:if test="parent::atom:feed">
      <xsl:variable name="key" select="zapi:key/text()"/>
      <button name="item_key" value="{$key}">Assign Abbreviation</button>
    </xsl:if>
    <p>	
      <xsl:apply-templates select="atom:title/text()"/>
    </p>
    <xsl:if test="atom:content[@type='xhtml']">
      <xsl:apply-templates select="atom:content/*"/>
    </xsl:if>
  </xsl:template>
</xsl:stylesheet>
		
