# say - speak messages aloud
This plugin uses a text-to-speech program to speak out any messages appearing in `environment/messages`. The TTS utility can be run on the Igor machine or on a machine that is accessible via _ssh_ (without a password).

## requirements

The plugin uses a command line utility `say`, as available on OSX. If `say` is not available it will try (in order) `espeak`, `flite` and `festival`, which are available on most Linux distributions. 

## schema

* `plugindata/say/voice`: string, the voice to use (default is to use the default voice). Not supported on Linux.
* `plugindata/say/remoteHost`: string, host on which to run the script (using _ssh_), default is the host Igor runs on. Only supported for OSX remote hosts.

## actions

When any element inside `environment/messages` is modified (usually these are `message` elements) the contents are spoken.