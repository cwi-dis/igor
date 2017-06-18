# lan - test availability of services

The lan plugin, which is badly named, tests availability of internet services. It works just as well for services on the LAN as for services out on the internet.

When the plugin runs, usually from a timed action in `actions`, it accepts a number of parameters as URL query parameters. It attempts to open a tcp-connection to a service on a given host/port combination, and fills a boolean value in `devices/_name_/alive` based on whether this is successful or not.

The following parameters are accepted:

* `name`: name of the service (string). This is used as the name of the element in `services` inside which the `alive` boolean is updated and `errorMessage` is set (if needed).
* `ip`: hostname or ip-address to contact (string). Default is to use the value of _name_.
* `port`: port to contact (integer), default 80.
* `timeout`: how many seconds to wait for the connection to be established before giving up (integer), default 5.

## schema

For each service _name_ there must be an entry `/data/services/_name_` which will be filled with with the following entries by the corresponding action:

* `alive`: a boolean telling whether the service is alive (and working correctly)
* `lastActivity`: a timestamp telling when the service was last contacted
* `errorMessage`: if this exists it is a string explaining in human-friendly language what is wrong with the service.

## examples

The plugin has two example _actions_, which test availability of a webserver at 192.168.1.1 (usually the internet router) and another one at google.com (where success indicates that the outside internet connection and various other services such as DNS are working):

```
<actions>
	<action>
		<interval>60</interval>
		<url>/plugin/lan?name=router&amp;ip=192.168.1.1</url>
	</action>
	<action>
		<interval>60</interval>
		<url>/plugin/lan?name=internet&amp;ip=google.com.</url>
	</action>
</actions>

```

