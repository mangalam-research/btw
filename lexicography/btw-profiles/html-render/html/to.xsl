<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet 
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:btw="http://lddubeau.com/ns/btw-storage"
    xmlns:zz="zz:zz"
    exclude-result-prefixes="tei html zz"
    version="2.0">
    <!-- import base conversion style -->
    <xsl:import href="/home/ldd/src/tei/trunk/Stylesheets/profiles/default/html/to.xsl"/>

  <xsl:param name="autoToc">false</xsl:param>
  <xsl:param name="numberHeadings">false</xsl:param>

  <xsl:param name="cssInlineFile">/home/ldd/Documents/mangalam/btw/design/storage-schemas/btw-profiles/html-render/html/btw.css</xsl:param>

  <!-- Local mappings -->
  <zz:lang-to-string>
    <zz:i from="sa-Latn">Sanskrit; Skt</zz:i>
    <zz:i from="pi-Latn">Pāli; Pāli</zz:i>
    <zz:i from="bo-Latn">Tibetan; Tib</zz:i>
    <zz:i from="zh-Hant">Chinese; Ch</zz:i>
    <zz:i from="x-gandhari-Latn">Gāndhārī; Gāndh</zz:i>
    <zz:i from="en">English; Eng</zz:i>
    <zz:i from="fr">French; Fr</zz:i>
    <zz:i from="de">German; Ger</zz:i>
    <zz:i from="it">Italian; It</zz:i>
    <zz:i from="es">Spanish; Sp</zz:i>
  </zz:lang-to-string>

  <xsl:variable name="btw:lang-to-string" select="document('')//zz:lang-to-string"/>
  
  <xsl:function name="btw:lang-to-abbr">
    <xsl:param name="lang"/>
    <xsl:variable name="r" select="tokenize($btw:lang-to-string/zz:i[@from=$lang]/text(), '; ')[2]"/>
    <xsl:if test="not($r)">
      <xsl:message terminate="yes">btw:lang-to-abbr: cannot convert <xsl:value-of select="$lang"/></xsl:message>
    </xsl:if>
    <xsl:value-of select="$r"/>
  </xsl:function>

  <xsl:function name="btw:lang-to-name">
    <xsl:param name="lang"/>
    <xsl:variable name="r" select="tokenize($btw:lang-to-string/zz:i[@from=$lang]/text(), '; ')[1]"/>
    <xsl:if test="not($r)">
      <xsl:message terminate="yes">btw:lang-to-name: cannot convert <xsl:value-of select="$lang"/></xsl:message>
    </xsl:if>
    <xsl:value-of select="$r"/>
  </xsl:function>

  <xsl:template name="btw:lang-to-abbr">
    <xsl:param name="lang" select="(ancestor-or-self::*/@xml:lang)[last()]"/>
    <xsl:variable name="abbr" select="btw:lang-to-abbr($lang)"/>
    <xsl:variable name="name" select="btw:lang-to-name($lang)"/>
    <xsl:variable name="frag">
      <xsl:choose>
	<!-- We do not need to treat the abbreviation as an abbreviation
	     if it turns out that the language it its own abbreviation.
	-->
	<xsl:when test="$abbr = $name">
	  <xsl:value-of select="$name"/>
	</xsl:when>
	<xsl:otherwise>
	  <tei:abbr corresp="/abbr/{$abbr}">
	    <xsl:copy-of select="$abbr"/>
	  </tei:abbr>
	</xsl:otherwise>
      </xsl:choose>
    </xsl:variable>
    <xsl:apply-templates select="$frag"/>
  </xsl:template>

  <xsl:template match="tei:form">
    <xsl:for-each-group select="*" group-by="@xml:lang">
      <xsl:for-each select="current-group()">
	<xsl:apply-templates select="."/>
	<xsl:if test="position() != last()">
	  <xsl:text>, </xsl:text>
	</xsl:if>
      </xsl:for-each>
      <xsl:if test="position() != last()">
	<xsl:text> / </xsl:text>
      </xsl:if>
    </xsl:for-each-group>
  </xsl:template>

  <xsl:template match="tei:orth">
    <span class="orth">
      <xsl:call-template name="makeLang"/>
      <xsl:apply-templates/>
    </span>
  </xsl:template>

  <xsl:template match="tei:seg[@type='sense']">
    <xsl:choose>
      <xsl:when test="@xml:id">
	<span id="{@xml:id}" class="sense">
	  <xsl:call-template name="makeLang"/>
	  <span class="sense-number">(<xsl:apply-templates select="@n"/>) </span> 
	  <xsl:apply-templates/>
	</span>
      </xsl:when>
      <xsl:otherwise>
	<xsl:apply-templates/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  
  <xsl:template match="tei:seg[@type='sense']" mode="xref">
    <span class="sense-number"><xsl:apply-templates select="@n"/>)</span>     
  </xsl:template>

  <xsl:template match="tei:cit">
    <!-- By default, all tei:cit elements become <div
         class="cit">. Also tei:cit elements are not mixed contents so
         whitespace between children is dropped. Add a space between
         all children of tei:cit. -->
    <span class="cit">
      <xsl:call-template name="makeLang"/>
      <xsl:choose>
	<xsl:when test="count(*) > 1">
	  <xsl:for-each-group select="*" group-starting-with="tei:quote">
	    <!-- Reorder the nodes so that tei:pron is first,
	         tei:quote is next, and the rest follows. -->
	    <xsl:for-each select="current-group()[self::tei:pron], current-group()[self::tei:quote], current-group()[not(self::tei:pron or self::tei:quote)]">
	      <xsl:apply-templates select="."/>
	      <xsl:if test="position() != last()">
		<xsl:text> </xsl:text>
	      </xsl:if>
	    </xsl:for-each>
	  </xsl:for-each-group>
	</xsl:when>
	<xsl:otherwise>
	  <xsl:apply-templates/>
	</xsl:otherwise>
      </xsl:choose>
    </span>
  </xsl:template>

  <xsl:template match="tei:cit/tei:bibl">
    <span class="bibl">
      <xsl:call-template name="makeLang"/>
      <xsl:apply-templates/>
    </span>
    <xsl:if test="count(preceding-sibling::*) = 0">
      <xsl:text>: </xsl:text>
    </xsl:if>
  </xsl:template>

  <!-- Special case for this context. -->
  <xsl:template match="tei:seg[@type='btw:lang' and tei:cit[@type='translation']]">
    <!-- 
	 There are two general contexts for this:
	  - As part of the classical transations. A list of these elements is terminated by a semi-colon.
	  - As part of the contemporary translations. A list of these elements is NOT terminated by a semi-colon but enclosed in a paragraph.
    -->

    <xsl:variable name="frag">
      <xsl:call-template name="btw:lang-to-abbr"/><xsl:text> </xsl:text>
      <xsl:apply-imports/>
      <xsl:if test="ancestor::tei:div[@type='btw:classical-translations'] and (following-sibling::* or normalize-space(following-sibling::text()))">
	<xsl:text>; </xsl:text>
      </xsl:if>
    </xsl:variable>
    <xsl:choose>
      <xsl:when test="ancestor::tei:div[@type='btw:classical-translations']">
	<xsl:copy-of select="$frag"/>
      </xsl:when>
      <xsl:when test="ancestor::tei:div[@type='btw:contemporary-translations']">
	<p>
	  <xsl:copy-of select="$frag"/>
	</p>
      </xsl:when>
      <xsl:otherwise>
	<xsl:message terminate="yes">Cannot determine handling of element.</xsl:message>
      </xsl:otherwise>

    </xsl:choose>
  </xsl:template>
  
  <xsl:template match="tei:seg[@type='btw:lang']/tei:cit">
    <xsl:next-match/>
    <xsl:if test="following-sibling::* or normalize-space(following-sibling::text())">
      <xsl:choose>
	<xsl:when test="ancestor::tei:div[@type='btw:classical-translations']">
	  <xsl:text>, </xsl:text>
	</xsl:when>
	<xsl:when test="ancestor::tei:div[@type='btw:contemporary-translations']">
	  <xsl:text>; </xsl:text>
	</xsl:when>
	<xsl:otherwise>
	  <xsl:message terminate="yes">Cannot determine handling of element.</xsl:message>
	</xsl:otherwise>
      </xsl:choose>
    </xsl:if>
  </xsl:template>

  <xsl:template match="tei:seg[@type='btw:lang']/text()">
    <xsl:if test="normalize-space()">
      <xsl:next-match/>
    </xsl:if>
  </xsl:template>

  <xsl:template match="tei:cit[@type='translation']/tei:note">
    <span>
      <xsl:call-template name="makeLang"/>
      <xsl:apply-templates/>
    </span>
  </xsl:template>

  <xsl:template match="tei:xr">
    <xsl:variable name="me" select="."/>
    <xsl:variable name="my-type" select="@type"/>
    <xsl:variable name="siblings-of-same-type" select="../tei:xr[@type = $my-type]"/>
    <xsl:if test="$siblings-of-same-type[1] = $me">
      <p class="xr">
	<xsl:choose>
	  <xsl:when test="$my-type = 'syn'">
	    synonyms:
	  </xsl:when>
	  <xsl:when test="$my-type = 'cog'">
	    cognates:
	  </xsl:when>
	  <xsl:when test="$my-type = 'ana'">
	    analogic: 
	  </xsl:when>
	  <xsl:when test="$my-type = 'con'">
	    contrastive: 
	  </xsl:when>
	  <xsl:when test="$my-type = 'cp'">
	    <xsl:attribute name="class" select="'xr-cp'"/>
	    <xsl:variable name="abbr">
	      <tei:abbr corresp="/abbr/Cp">Cp.</tei:abbr>
	    </xsl:variable>
	    <xsl:apply-templates select="$abbr"/> also
	  </xsl:when>
	  <xsl:otherwise>
	    <xsl:message terminate="yes">Unsupported tei:xr type: <xsl:value-of select="$my-type"/></xsl:message>
	  </xsl:otherwise>
	</xsl:choose>
	<xsl:for-each select="$siblings-of-same-type">
	  <span class="xr">
	    <xsl:call-template name="makeLang"/>
	    <xsl:apply-templates/>
	  </span>
	  <xsl:if test="position() != last()">
	    <xsl:text>, </xsl:text>
	  </xsl:if>
	</xsl:for-each>
      </p>
    </xsl:if>
  </xsl:template>

  <xsl:template match="tei:abbr">
    <a>
      <xsl:attribute name="href">
	<xsl:value-of select="@corresp"/>
      </xsl:attribute>
      <xsl:apply-templates/>
    </a>
  </xsl:template>

  <!-- Override this TEI template to have no headers. -->
  <xsl:template name="stdheader">
    <xsl:param name="title"/>
  </xsl:template>

  <!-- Override this TEI template to have no footers. -->
  <xsl:template name="stdfooter"/>

  <xsl:template name="cssHook">
    <style type="text/css">
      <!-- The following select excludes English language values, and
           text marked as being Chinese using Hanzi. Using lang(...)
           is cleaner than doing string tests.
      -->
      <xsl:for-each-group 
	  select="//@xml:lang" 
	  group-by=".">
	<xsl:choose>
	  <xsl:when test="lang('en')">
	    [lang="<xsl:value-of select="."/>"] { font-style: normal; }
	  </xsl:when>
	  <xsl:when test="lang('zh-Hant')">
	    <!-- pass -->
	  </xsl:when>
	  <xsl:otherwise>
	    [lang="<xsl:value-of select="."/>"] { font-style: italic; }
	  </xsl:otherwise>
	</xsl:choose>
      </xsl:for-each-group>
    </style>
  </xsl:template>
</xsl:stylesheet>
