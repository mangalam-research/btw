<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    version="2.0">
  <xsl:output method="xml" indent="no"/>

  <!--
       Initially this was meant to actually combine a schema and its
       imports into a single file but that proved more challenging
       than anticipated. (Flattening a Relax NG schema is trivial but
       flattening an XSD does not seem as simple.)

       Instead of actually flattening, we save the imports locally and
       modify the initial schema to load locally. Note that the
       current solution is not recursive. It would have to be modified
       to generate unique file names.

       Why this? We don't want to make network requests every damn
       time we use the a schema that has network imports. Besides the
       repeated network requests, it is also a problem when the
       servers are down, which **has** happened. (Yep, Library of
       Congress, down.) It is also a problem when working offline
       (e.g. on a plane).
  -->

  <!-- Imports are inlined -->
  <xsl:template match="xs:import">
    <xsl:variable name="schema" select="@schemaLocation"/>
    <xsl:variable name="file_name" select="concat(position(), '.xsd')"/>
    <xsl:result-document method="xml" href="{$file_name}">
      <xsl:copy-of select="document($schema)"/>
    </xsl:result-document>
    <xs:import>
      <xsl:apply-templates select="@* except @schemaLocation"/>
      <xsl:attribute name="schemaLocation" select="$file_name"/>
    </xs:import>
  </xsl:template>

  <!-- We just copy everything else -->
  <xsl:template match="node() | @*">
    <xsl:copy>
      <xsl:apply-templates select="node() | @*"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
