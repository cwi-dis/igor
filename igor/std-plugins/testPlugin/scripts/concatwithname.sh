#!/bin/bash
# First part of the test: call updateStatus
cat << endcat | igorVar --post application/json --checkdata /internal/updateStatus/devices/$igor_pluginName
{ "alive" : true,
  "resultData" : "$igor_arg"
}
endcat
# Second part of the test: return the concatenation of the plugin name and the argument.
echo "This is the test script for $igor_pluginName. Concatenating that with arg gives $igor_pluginName$igor_arg."
