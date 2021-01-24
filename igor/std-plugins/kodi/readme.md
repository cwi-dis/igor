# Kodi - control Kodi media player

This plugin controls a [Kodi](https://kodi.tv) entertainment system. It allows controlling playback of media items and such, and
reports status information on when Kodi is currently playing. Uses the [Kodi JSONRPC](https://kodi.wiki/view/JSON-RPC_API) interface over HTTP.

There is no support for 
## schema

* `environment/mediaPlayback`: Information on what audio/video/TV/Music is currently being playing
* `devices/kodi/current`: current status of Kodi, what it is currently doing
* `devices/kodi/target`: commands for Kodi, what it should be doing
* `plugindata/kodi/url`: URL to access Kodi JSONRPC end point

## requirements

Use of this plugin requires access to a Kodi media player.

## actions

* Periodically retreive Kodi current status to `devices/kodi/current`
* Transmit commands to Kodi whenever `devices/kodi/target` changes
* Update `environment/mediaPlayback` from `devices/kodi/current`