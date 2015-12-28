<?xml version="1.0" encoding="iso-8859-1"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
	xmlns="http://www.w3.org/1999/xhtml">

	<xsl:template match="/root">
		<html>
		<head><title>Server Dump</title></head>
		<body>
		<h1>Server Dump</h1>
		<p>This is the server dump</p>
		<h2>Service Status</h2>
		<xsl:apply-templates match="services"/>
		<h2>Connected Clients</h2>
		<xsl:apply-templates match="clients"/>
		<h2>Cue Queue</h2>
		<xsl:apply-templates match="cues"/>
		<h2>Optimizer-generated Restrictions to Orchestrator</h2>
		<xsl:apply-templates match="restrictions"/>
		<h2>Orchestrator-generated Decisions to Dispatcher</h2>
		<xsl:apply-templates match="decisions"/>
		<h2>Dispatcher Instructions to Video Router</h2>
		<xsl:apply-templates match="connections"/>
		</body>
		</html>
	</xsl:template>

	<xsl:template match="services">
		<table>
		<tr><th>Service</th><th>Last execution</th></tr>
		<xsl:for-each select="*">
		<tr>
			<td><xsl:value-of select="local-name()"/></td>
			<td><xsl:value-of select="lastRun"/></td>
		</tr>
		</xsl:for-each>
		</table>
	</xsl:template>
	<xsl:template match="clients">
		<table>
		<tr><th>Client</th><th>User</th><th>Sources</th><th>Sinks</th></tr>
		<xsl:for-each select="*">
		<tr>
			<td><xsl:value-of select="local-name()"/></td>
			<td><xsl:value-of select="user"/></td>
			<td><xsl:for-each select="sources/*"><xsl:value-of select="local-name()"/>, </xsl:for-each></td>
			<td><xsl:for-each select="sinks/*"><xsl:value-of select="local-name()"/>, </xsl:for-each></td>
		</tr>
		</xsl:for-each>
		</table>
	</xsl:template>
<!--

	<xsl:template match="cues">
		<p><b><xsl:value-of select="."/></b></p>
	</xsl:template>

	<xsl:template match="restrictions">
		<p><b><xsl:value-of select="."/></b></p>
	</xsl:template>

	<xsl:template match="decisions">
		<p><b><xsl:value-of select="."/></b></p>
	</xsl:template>

	<xsl:template match="connections">
		<p><b><xsl:value-of select="."/></b></p>
	</xsl:template>
-->
</xsl:stylesheet>
