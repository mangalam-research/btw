<?xml version="1.0" encoding="utf-8"?>
<iso:schema
    xmlns="http://purl.oclc.org/dsdl/schematron"
    xmlns:iso="http://purl.oclc.org/dsdl/schematron"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    queryBinding="xslt2"
    schemaVersion="ISO19757-3">
  <!--
       ATTENTION:

       This code duplicates the check in btw_validator. Changes there
       should be mirrored here and changes here should be mirrored there.

  -->
  <iso:title>Validation Schema for btw-schema-0.10 files.</iso:title>
  <iso:ns prefix="btw" uri="http://mangalamresearch.org/ns/btw-storage"/>
  <iso:ns prefix="tei" uri="http://www.tei-c.org/ns/1.0"/>
  <iso:pattern>
    <iso:rule context="btw:sense">
      <iso:assert test="count(.//btw:sf[not(ancestor::btw:contrastive-section | ancestor::btw:english-rendition)])">
	Sense without semantic fields.
      </iso:assert>
    </iso:rule>
    <iso:rule context="btw:cognate">
      <iso:assert test="count(.//btw:sf)">
	Cognate without semantic fields.
      </iso:assert>
    </iso:rule>
    <iso:rule context="btw:sf">
      <!-- We use replace(...) to convert the \s patterns to something
           equivalent to what \s matches in JavaScript regular expressions. -->
           \f (#x000c) and \v (#x000b) are missing as they are not valid
           characters in XML. -->
      <iso:assert test="matches(text(), replace('^\s*\d{2}(\.\d{2})*(\s*\|\s*\d{2}(\.\d{2})*)?(aj|av|cj|in|n|p|ph|v|vi|vm|vp|vr|vt)?\s*$', '\\s', '[ \\n\\r\\t&#x00a0;&#x1680;&#x180e;&#x2000;&#x2001;&#x2002;&#x2003;&#x2004;&#x2005;&#x2006;&#x2007;&#x2008;&#x2009;&#x200a;&#x2028;&#x2029;&#x202f;&#x205f;&#x3000;]'))">
	Semantic field in an incorrect format.
      </iso:assert>
    </iso:rule>
    <iso:rule context="tei:surname">
      <iso:assert test="text()">
        Surname cannot be empty.
      </iso:assert>
    </iso:rule>
    <iso:rule context="btw:credits">
      <iso:assert test="tei:editor">
        An article must have at least one editor.
      </iso:assert>
      <iso:assert test="btw:credit">
        An article must have at least one author.
      </iso:assert>
    </iso:rule>
  </iso:pattern>
</iso:schema>
