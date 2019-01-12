# lan - test availability of services

The lan plugin, which is badly named, tests availability of internet services. It works just as well for services on the LAN as for services out on the internet.

When the plugin runs, usually from a timed action in `actions`, it accepts a number of parameters as URL query parameters. It attempts to open a tcp-connection to a service on a given host/port combination, and returns either `ok` or an error message. The plugin also sets the status of the service in `status/services/_name_/alive` and others based on whether this is successful or not.

The following parameters are accepted:

* `name`: name of the service (string).
* `ip`: hostname or ip-address to contact (string). Default is to use the value of _name_.
* `port`: port to contact (integer), default 80.
* `timeout`: how many seconds to wait for the connection to be established before giving up (integer), default 5.
* `url`: alternative to _ip/port/timeout_, try to connect to a http[s]-based service.
* `service`: where status report will be posted. Default is `services/%s`, where the `name` is filled in for the `%s`.

## schema

For each service _name_ there will be an entry `/data/status/services/_name_` which will be filled with with the following entries by the corresponding action:

* `alive`: a boolean telling whether the service is alive (and working correctly)
* `lastSuccess`: a timestamp telling when the service was most recently contacted successfully
* `lastFailure`: a timestamp telling when the service was most recently not contacted successfully
* `lastActivity`: a timestamp telling when the plugin was run most recently
* `errorMessage`: if this exists it is a string explaining in human-friendly language what is wrong with the service.

## user interface

There is a user interface at _/plugin/lan/page/index.html_ that allows inspecting/adding/deleting lan plugin watchers.
It also has some suggested actions to add, to test internet health and Igor health.