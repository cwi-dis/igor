# smartmeter_iotsa - read current household energy use

This plugin interfaces to a _iotsa p1 reader_ <https://github.com/cwi-dis/iotsaSmartMeter>. It consists of an esp8266 that interfaces to the standardised dutch smart meter p1 port, see [DSMR v2.2](http://www.netbeheernederland.nl/themas/dossier/documenten/).

It reads all information including current electricity and gas use, electricity delivered back to the net, total consumption, etc.

## requirements

* A dutch smart energy meter.
* A iotsa p1 reader.

## schema

* `sensors/smartMeter`: raw data read from the smart meter:
	* `timestamp`: Time of reading, as provided by the smart meter itself (isotime).
	* `meter_id_electricity` and `meter_id_gas`: unique IDs of the meters (string).
	* `current_kw`: Current electricity use in kW (float).
	* `total_kwh_tariff_1`: Total electricity use under normal tariff over meter lifetime (kWh, float).
	* `total_kwh_tariff_2`: Total electricity use under reduced (night) tariff over meter lifetime (kWh, float).
	* all of those are also available with `_returned` appended for delivery back to the net.
	* `current_tariff`: integer, 1 or 2 depending on day or night.
	* `total_power_failures`: total number of power failures over device lifetime (integer).
	* `total_power_failures_`: total number of long power failures over device lifetime (integer).
	* `total_gas_m3`: Total gas consumption over meter lifetime (float).
	* `unkown`: Other readings. This element has a `tag` attribute with the DSMR identifier and the data is a string with the unparsed DSMR content.
* `plugindata/smartmeter_iotsa/host`: string, host name or IP address of the iotsa p1 reader.
* `plugindata/smartmeter_iotsa/protocol`: protocol to access the iotsa p1 reader (`http`, `https` or `coap`).

## internal actions

* Once every minute the smart meter is read and the data deposited into `sensors/smartMeter`.
* Whenever the data in `sensors/smartMeter` is changed `environment/energy/electricity` is updated.