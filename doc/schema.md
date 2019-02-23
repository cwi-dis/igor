# Igor database schema

While there is very little in Igor that is hard-coded
here is the schema that is generally used by Igor databases. 

The (preliminary) schema for access control can be found in the separate document [capabilities.md](capabilities.md).

The toplevel element is called `data`. Usually you can refer to the children of the toplevel element using a relative path such as `environment/location`, sometimes (within expressions triggered by events, for example) you must refer by absolute path, then you should use `/data/environment/location`.

There is no formal schema, but in the descriptions of the leaf elements below we specify the type expected:

* _integer_, _float_: the usual. Encoded as strings in XML, should be converted to native values in JSON.
* _string_: UTF-8 unicode string. Represented with the usual XML escaping in XML.
* _timestamp_: _integer_ value representing seconds since the Unix epoch (1-Jan-1970 00:00 UTC).
* _isotime_: String representing local date and time in ISO-8601 human-readable form, for example `2017-04-14T14:25:09`.
* _boolean_: because XPath 1.0 has no concept of booleans and to facilitate round-tripping to JSON an empty value should be used for _false_ and the string `true` for _true_.

There is an escape mechanism to use when a variable name would be illegal as an XML tag name. The following two XML code fragments are identical:

```
<abcd>efg</abcd>
```
```
<_e _e="abcd">efg</_e>
```
but in the latter `abcd` can be any string. Round-tripping to JSON of this construct is transparent.

In various elements XPath expressions can be used. These follow XPath 1.0, with a number of extensions:

* `$originalContext` is available in _action_ XPaths and refers to the element that triggered the action.
* `igor_dateTime(number)` converts a _timestamp_ to an _isotime_. When called without argument it returns the current date and time.
* `igor_timestamp(isotime)` converts an _isotime_ to a _timestamp_. When called without argument it returns the current time.
* `igor_year_from_dateTime(isotime)` and similar functions from XPath 2.0 are available with the `igor_` prefix.
* `igor_date_equal(isotime, isotime)`, `igor_time_equal(isotime, isotime)`, `igor_dateTime_equal(isotime, isotime)` and the usual variations are available for comparing dates, times and date-time combinations.
* `igor_ifelse(expr1, expr2)` returns _expr1_ if it is true, otherwise _expr2_.
* `igor_ifthenelse(expr1, expr2, expr3)` If _expr1_ is true returns _expr2_, otherwise _expr3_.

## environment

Stores high level information about the environment (household) in which Igor is operating such as GPS location.

### environment/night
Nonzero if it is considered night. Set by standard action _checkNight_, used by various plugins to refrain from actions like turning on loud devices.

### environment/location
GPS location of the home. Used by plugins like _buienradar_ to get rain forecasts for the correct place. Generally initialized by the user (but could be done using a GPS plugin).

* `lat`: lattitude (float).
* `lon`: longitude (float).

### environment/energy
Current energy consumption information. Indirectly set by plugins like _smartmeter_.

* `electricity`: current electricity consumption in kWh (float).

### environment/weather
High-level information about temperature and such. Indirectly set by plugins like _netatmo_.

* `tempInside`: temperature inside in degrees Celcius (float).
* `tempOutside`: temperature outside in degrees Celcius (float).

### environment/people
Information about people that is not considered privacy-sensitive:

* `count`: number of people on the premises

### environment/messages
Informational messages produced by various plugins (or by external agents with a `POST` through the REST inferface). New messages will be picked up by plugins like _lcd_ or _say_ to present them to the user. Standard action _cleanup_ will remove them after a while.

* `message`: a text string to be shown or spoken to the user (string).

### environment/devices
A set of boolean values indicating that devices of which the end user is aware (such as mobile phones or keyring transponders) are in the house and active. Names should be user-friendly. The intention is that this category is used specifically for devices that are portable, and that are carried around by people (or dogs, or cars, or bicycles). These values are set by plugins like _dhcp_, after converting MAC-addresses to user-friendly names based on information in _plugindata_. Values here are used by rules from _actions_ to populate _people_.

Example value:

* `laptopJack`: true if Jack's laptop is in the house (boolean).

### environments/lights
(_Unused, currently_) A set of booleans indicating the state of lights (or actually any electric device controllable through a smart outlet or something similar). These may be write-only, as reading the state of light switches is often impossible. The names should be human-readable, and changes in the values are picked up by plugins like _kaku_ to turn on or off those lights (after converting the names to switch IDs through information in _plugindata_).

Example value:

* `diningRoomTable`: boolean, set to true or false to turn this light on or off.

### environment/systemHealth

High-level information about how the technical infrastructure of the household (such as the internet connection, and Igor itself) is functioning. The _systemHealth_ plugin maintains this, from low-level information in `/data/status`.
_systemHealth_ creates entries in `environment/systemHealth/messages` with descriptive names and user-readable text. These entries are removed when the anomalous condition no longer exists. For example:

```
<systemHealth>
	<messages>
		<internet>It seems the internet connection is down.</internet>
	</messages>
</systemHealth>
```
The user can silence anomalous conditions he or she knows about (and does not want to be bothered with) for a period of time by setting fields in `/data/status`.

## status

Status information on everything Igor knows about, such as whether services and devices are functioning, when they were last accessed correctly and any error messages produced. Updated by `/internal/updateStatus`, governed by the `representing` variable in actions and such. Interpreted by the _systemHealth_ plugin, among others.

Each entry has a number of fields:

- `alive` (boolean) true if last attempt to access the device or service was successful.
- `errorMessage` (string, optional) human-readable error message in case last attempt was unsuccessful.
- `lastActivity` (timestamp) time of the last attempt to access the device or service.
- `lastSuccess` (timestamp, optional) time of the most recent successful access.
- `lastFailure` (timestamp, optional) time of the most recent unsuccessful access.
- `ignoreErrorsUntil` (timestamp, optional) "silencing" timestamp, the [systemHealth](std-plugins/systemHealth/readme.md) plugin will not complain about errors in this entry until the given time.

Entries are grouped by their type:

- `status/igor` Igor components, insofar they can be tested separately:
	- `status/igor/start` Igor main server startup. This entry has a few more fields beside the ones listed above:
		- `status/igor/start/url`: Base URL to use with `igorVar --url` (string).
		- `status/igor/start/host`: Host name on which this Igor instance runs (string).
		- `status/igor/start/port`: Port on which this Igor listens (integer).
		- `status/igor/start/version`: Igor version (string).
		- `status/igor/start/count`: How often this Igor instance has been (re)started.
	- `status/igor/core` the Igor main server loop
	- `status/igor/save` saving the Igor database to disk
	- `status/igor/web` the external HTTP interface to Igor
- `status/sensors` Sensors, or sensor categories (for sensors such as [ble](std-plugins/ble/readme.md) where a single plugin handles multiple sensors. Entries are named for the sensor or category.
- `status/devices` Devices (actuators and appliances). Entries are named for the individual device.
- `status/services` Services external to Igor, for which only status information is kept. Some examples:
	- `status/services/internet` whether the internet connection works. Determined by the [lan plugin](std-plugins/lan/readme.md) by trying to access _google.com_.
	- `status/services/backup` whether Time Machine backups are made. Determined by the [timemachine plugin](std-plugins/timemachine/readme.md).

## sensors

Stores low level information from devices that are generally considered read-only such as temperature sensors. See the descriptions of the individual plugins for details:

* `sensors/dhcp`: DHCP leases. See [dhcp plugin readme](std-plugins/dhcp/readme.md).
* `sensors/ble`: Visible Bluetooth LE devices. See [ble plugin readme](std-plugins/ble/readme.md).
* `sensors/rfid`: RFID tags recently presented. See [iirfid plugin readme](std-plugins/iirfid/readme.md) and [homey plugin readme](std-plugins/homey/readme.md).
* `sensors/tags`: Named RFID tags recently presented. See [iirfid plugin readme](std-plugins/iirfid/readme.md) and [homey plugin readme](std-plugins/homey/readme.md).
* `sensors/netAtmo`: Weather data. See [netatmo plugin readme](std-plugins/netatmo/readme.md).
* `sensors/smartMeter`: Energy consumption. See [smartMeter plugin readme](std-plugins/smartmeter_iotsa/readme.md).
* `sensors/fitbit`: Health data. See [fitbit plugin readme](std-plugins/fitbit/readme.md).
* `sensors/buienradar`: Expected rainfall data. See [buienradar plugin readme](std-plugins/buienradar/readme.md) and [neoclock plugin readme](std-plugins/neoclock/readme.md).


## devices

Stores low level information for devices that are write-only (actuators, such as motors to lower blinds) or read-write (applicances such as television sets). For writable devices such as actuators there are usually rules in _actions_ that take care of changing the state of the actuator when values in this section are changed.

See the descriptions of the individual plugins for details:

* `devices/tv`: Television set, information like power status, current channel, etc. See [philips plugin readme](std-plugins/philips/readme.md).
* `devices/plant`: Current position of the movable plant, see [plant plugin readme](std-plugins/plant/readme.md).
* `devices/lcd`: Adding a new `devices/lcd/message` will result in this message being displayed. See [lcd plugin readme](std-plugins/lcd/readme.md).

## people

Stores high level information about actual people, such as whether they are home or not. Names in the _people_ section match names in the _identities_ section.

The intention about the separation between _people_ and _environment/people_ is that the latter is available to everyone who has access to the database, while the
former is only accessible to users who have logged in (assuming capability-based access control is enabled). The data in _identities/username_ is even more protected
and only available to that specific user. So, _identities/username_ can contain contain private information (such as hardware address of mobile phone), _people/username_
can contain semi-private information (such as whether _username_ is at home or not) and _identities/people_ non-private information (such as the number of people currently at home).

As an example:

* `people/jack/home`: Boolean that indicates whether a use "jack" is considered to be in the house (as determined by rules that trigger on his devices).


## identities

Stores identifying information about people, such as the identity of their cellphone or login information for cloud-based health data storage.

As an example:

* `identities/jack/encryptedPassword` The encrypted Igor password for user _jack_. Verified by the `/login` entry point, after which the user identity is stored in the session, or when supplied through the HTTP `Authorization: Basic` header.
* `identities/jack/plugindata`: Per-user data for plugins. For example:
	* `identities/jack/plugindata/fitbit`: Information that allows the [fitbit plugin](std-plugins/fitbit/readme.md) to obtain health information for user "Jack".
* `identities/jack/device`: Name of a device that user "Jack" tends to carry with him (string).

If capability support is enabled, identity entries will also carry the set of capabilities for that user, but these are inaccessible during normal operation.

A special user _admin_ will carry a set of _master capabilities_.

## actions

Stores triggers and actions that operate on the database. *(this name is hardcoded in the Igor implementation)* Action elements can also be present
inside `plugindata` children.

Actions can be triggered by external access, timers, conditions in the database or a combination of those:

* Actions that are named, for example `save`, can be triggered by external means (by accessing `http://igor.local:9333/action/save`). Multiple actions can have the same name, and external access will trigger all of them.
* Actions can have an interval and will then be triggered periodically.
* Actions can have an XPath expression and will the be triggered whenever any database element matching this expression is modified. As an example, the `save` action above has an expression of `/data/identities//*` resulting the in the database being saved whenever anything in the _identities_ section is changed.

When an action is triggered a number of conditions is tested to see whether the action actually needs to be run or not:

* It is possible to specify that an action should not be run before a certain time.
* It is possible to specify that an action should not be run more often than a given minimum time interval.
* It is possible to specify a database condition (as an XPath expression) to determine whether the action should be run or not.

If the condition is met then the action is run. This takes the form of an HTTP operation on a URL, possible with data to provide to the operation. The url and data fields support the use of XPath expressions inside curly braces `{` and `}` (Attribute Value Templates, AVTs, such as used in XForms and SMIL, for example).

If the action is triggered by an XPath expression then the XPath expressions within the action (such as in an AVT or condition) are run in a context with the triggering element as the current node. The triggering element is also available as the `$originalContext` variable, so if the expression changes the context you can still refer to the triggering node.
 
Here is a description of the available elements:

* `actions/action/name`: Name of the action (string). Action will trigger when `/actions/name` is accessed.
* `actions/action/xpath`: XPath expression that must deliver a _node_ or _nodeset_ (string). Action will trigger if any of these nodes is modified.
* `actions/action/multiple`: A boolean that signals what should happen if multiple elements are changed (and match the xpath expression) by the same operation. When false (the default) the action triggers once, with a random element as the context. When true the action will trigger for each element in the nodeset.
* `actions/action/aggregate`: A boolean to indicate that multiple triggers of this action can be aggregated into a single call. Note that this is completely different from `multiple`, it can be used to forestall scheduling an action if the identical action is already waiting to be executed.
* `actions/action/interval`: Interval in seconds (integer). Action will trigger at least once every _interval_ seconds.
* `actions/action/minInterval`: Minimum interval in seconds (integer). Action will trigger at most once every _minInterval_ seconds.
* `actions/action/notBefore`: Earliest time this action will trigger again (timestamp). This field is set by Igor whenever the action is triggered, using data from _minInterval_, and it is actually the way the _minInterval_ functionality is implemented.
* `actions/action/condition`: XPath expression that is evaluated whenever a trigger has happened and that must return _true_ for the action to be executed. 
* `actions/action/url`: The URL to which a request should be made (string). AVTs can be used in this field. This is the only required field.
* `actions/action/method`: The method used to access the url, default GET (string).
* `actions/action/data`: For POST and PUT methods, the data to supply to the operation (string). Can use AVTs.
* `actions/action/mimetype`: The MIME type of _data_ (string), default `text/plain`.
* `actions/action/representing`: The entity on whose behalf this action runs (string), for reporting in _systemHealth_.
* `actions/action/creator`: The plugin that created this action (string), for showing the action in the plugin UI.

If capabilities are enabled each action can carry a set of capabilities and the _actions_ element itself can also carry a set (that will be inherited by each action).

### Standard actions

There are a number of standard actions, which are used by Igor itself or used to fill some of the standard elements in the database. Multiple actions with the same name can exist, and all of them will fire (so you can add actions to do additional things if these events happen). These actions (by _name_) are:

* _start_: fired when Igor is started (automatically by Igor). 
* _save_: saves the in-memory copy of the database to the external file. Called periodically, and whenever a part of the database that is somehow considered important is changed.
* _cleanup_: deletes old elements in `environment/messages` and such.
* _updateActions_: updates the internal action datastructure whenever elements are added (not changed) in `actions`.
* _checkNight_: maintains the value of `environment/night`.
* _updatePeople_: updates people availability in `people` when device availability in `environment/devices` changes.
* _countPeopleAtHome_: updates `environment/people/count` when people availability changes.

## sandbox

Does nothing special, specifically meant to play with `igorVar` and REST access and such.

## eventSources

Contains references to Server-Sent event (SSE) sources, and where in the database the resulting values should be stored. Each event source will create a listener thread that opens a connection to the source and updates the database as events come in. Event types and event IDs are currently ignored, only the SSE _data_ field is used.

* `eventSources/eventSource/src`: URL of the SSE endpoint to connect to (string).
* `eventSources/eventSource/srcMethod`: Method used to access the _src_ url (string), default GET.
* `eventSources/eventSource/dst`: URL where the SSE _data_ should be sent to (string).
* `eventSources/eventSource/dstMethod`: Method used to access the _dst_ url (string), default PUT.
* `eventSources/eventSource/mimetype`: How the _data_ field should be interpreted (and how it is forwarded to _dst_). Default `application/json`.

## plugindata

Contains per-plugin configuration data, such as the mapping of hardware network addresses (MAC addresses) to device names. Can also contain
_action_ elements (for actions that are specific to the plugin implementation). These actions will run with all the access control rights of
the plugin itself.

See the descriptions of the individual plugins for details on per-plugin data.
