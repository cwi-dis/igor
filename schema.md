# Igor database schema

While there is very little in Igor that is hard-coded
here is the schema that is generally used by Igor databases. 

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

### environment/messages
Informational messages produced by various plugins (or by external agents with a `POST` through the REST inferface). New messages will be picked up by plugins like _lcd_ or _say_ to present them to the user. Standard action _cleanup_ will remove them after a while.
* `message`: a text string to be shown or spoken to the user (string).

### environment/devices
A set of boolean values indicating that devices of which the end user is aware (such as mobile phones) are in the house and active. Names should be user-friendly. These values are set by plugins like _dhcp_, after converting MAC-addresses to user-friendly names based on information in _plugindata_. Values here are used by rules from _actions_ to populate _people_.

Example value:

* `laptopJack`: true if Jack's laptop is in the house (boolean).

### environment/systemHealth

**(this section is expected to change soon)**

High-level information about how the technical infrastructure of the household (such as the internet connection, and Igor itself) is functioning. Used by plugins like _neoclock_ to inform the user of anomalous conditions. Health-checking actions are expected to create entries in `environment/systemHealth/messages` with descriptive names and user-readable text. These entries should be removed when the anomalous condition no longer exists. For example:

```
<systemHealth>
	<messages>
		<internet>It seems the internet connection is down.</internet>
	</messages>
</systemHealth>
```
The intention is that there will be a mechanism whereby the user can silence anomalous conditions he or she knows about (and does not want to be bothered with) for a period of time.

### environment/introspection
Information about activity of various plugins and Igor itself.

#### environment/introspection/lastActivity
For most plugins, an _isotime_ telling when the plugin was last active. `igor` should reflect the last activity of igor itself (but does not seem to work at the moment).

#### environment/introspection/rebootCount
An _integer_ telling how many times Igor was succesfully restarted on this database.

## sensors

Stores low level information from devices that are generally considered read-only such as temperature sensors.

## devices

Stores low level information for devices that are write-only (actuators, such as motors to lower blinds) or read-write (applicances such as television sets).

## people

Stores high level information about actual people, such as whether they are home or not.

## identities

Stores identifying information about people, such as the identity of their cellphone or login information for could-based healt data storage.

## actions

Stores all the triggers and actions that operate on the database. *(this name is hardcoded in the Igor implementation)*

## sandbox

Does nothing special, specifically meant to play with `igorVar` and REST access and such.

## eventSources

Contains references to Server-Sent event (SSE) sources, and where in the database the resulting values should be stored.

## plugindata

Contains per-plugin configuration data, such as the mapping of hardware network addresses (MAC addresses) to device names.