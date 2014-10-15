<?xml version="1.0" encoding="utf-8"?>
<iso:schema
    xmlns="http://purl.oclc.org/dsdl/schematron"
    xmlns:iso="http://purl.oclc.org/dsdl/schematron"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    queryBinding="xslt2"
    schemaVersion="ISO19757-3">
  <!--
       ATTENTION:

       This code duplicates the check in btw_validator. Changes there should
       be mirrored here and changes here should be mirrored there.

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
  </iso:pattern>
</iso:schema>
