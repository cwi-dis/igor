# lcd - show messages on an LCD display

This plugin is normally called in an _action_ that is triggered whenever a new `environment/messages/message` appears. It displays that message on an external LCD display.

See the [say plugin](../say/readme.md) for an alternative way to present messages to the user (by speaking them).

## requirements

To use the plugin as-is (as opposed to using it as sample code for other ways to display messages) requires a command line tool `lcdecho`. This tool is available as part of the [iotsa Display Server], _URL to be provided later_.

## actions

One action, to display the content of any element inside `environment/messages` whenever it changes.