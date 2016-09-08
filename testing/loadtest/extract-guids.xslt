<?xml version="1.0"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform"  >
<xsl:output method="text" omit-xml-declaration="yes" standalone="no" />
		
<xsl:template match="/">
<guids>
	<xsl:for-each select="rss/channel/item">
		    <guid><xsl:value-of select="guid/text()"/></guid>
	</xsl:for-each>
</guids>
</xsl:template>

<xsl:template match="*" mode="copy">
  <xsl:element name="{name()}" namespace="{namespace-uri()}">
    <xsl:apply-templates select="@*|node()" mode="copy" />
  </xsl:element>
</xsl:template>

<xsl:template match="@*|text()|comment()" mode="copy">
  <xsl:copy/>
</xsl:template>

</xsl:stylesheet>