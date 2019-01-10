# netatmo - get environmental data from a NetAtmo weather station

This plugin gets data from a [NetAtmo](http://netatmo.com) weather station through their cloud API.

Raw data is stored in `sensors/netatmo` with one element per weather station (using the names the user assigned to the stations).

Some parsed weather data is stored in `environment/weather`, in a slightly ad-hoc way: inside temperature is taken from any station that has a wifi interface, outside temperature from any station with an RF interface.

The plugin could also be adapted to get data from other NetAtmo sensors.

## requirements

* a NetAtmo weather station

You will need to register your Igor with the NetAtmo cloud service, to tell NetAtmo that it is okay that
Igor gets your (possibly privacy-sensitive) weather data.

The _setup.html_ page should help you doing this.

### Manual registration

If the _setup.html_ page does not work for you you can set registration up manually.


## schema

* `plugindata/netatmo/authentication` Authentication parameters:
	* `clientId` String of hexadecimal digits identifying your Igor, from _dev.netatmo.com_.
	* `clientSecret` Longer string of alfanumeric characters identifying your Igor, from _dev.netatmo.com_.
	* `username` Your personal username, from _netatmo.com_.
	* `password` Your personal password, from _netatmo.com_.
* `sensors/netatmo/_stationname_` Data for one weather station (base station or extension)
* `environment/weather/tempInside` Current indoor temperature
* `environment/weather/tempOutside` Current outdoor temperature

