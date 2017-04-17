# buienradar - buienradar.nl plugin

Stores rain forecast for the coming hour, from data provided by [buienradar.nl](http://buienradar.nl).

## requirements

GPS location in `environmnt/location` is used to get rain forecast data, and this location must probably be in the Netherlands.

## schema

* `sensors/buienradar/lastupdate`: timestamp of last update.
* `sensors/buienradar/data`: one 5-minute rain forecast. Multiple elements can exist, they should be ordered temporally. Fields:
	* `mm`: amount of rain expected, in millimeters (float)
	* `level`: logarithmic value of above, see buienradar API for details (integer)
	* `time`: date and time for which this measurement is valid (isotime)
	* `hour`: hour of `time` (int)
	* `minute`: minute of `time` (int)
* `plugindata/buienradar`: GPS location for which to present forecast. 
	
## actions

Three actions:

* Use buienradar.nl API to fill `sensors/buienradar` every 5 minutes.
* Copy `environment/location/lon` to `plugindata/buienradar/lon` on Igor start and whenever it changes.
* Copy `environment/location/lat` to `plugindata/buienradar/lat` on Igor start and whenever it changes.
