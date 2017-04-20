# say - speak messages aloud
This plugin uses a text-to-speech program to speak out any messages appearing in `environment/messages`. The TTS utility can be run on the Igor machine or on a machine that is accessible via _ssh_ (without a password).

## requirements

The plugin as distributed requires a command line utility `say`, as available on OSX, but it is trivial to modify it to use `espeak` or some other TTS package. 

## schema

* `plugindata/say/voice`: string, the voice to use (default is to use the default voice).
* `plugindata/say/remoteHost`: string, host on which to run the script (using _ssh_), default is the host Igor runs on.

## actions

When any element inside `environment/messages` is modified (usually these are `message` elements) the contents are spoken.