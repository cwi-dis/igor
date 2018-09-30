# systemHealth - look after health of services and other infrastructure

This plugin checks services, sensors and devices for error messages and aggregates these. It is triggered
by the _systemHealth_ action. It works together with the `/systemHealth.html` template document and the _neoclock_ plugin (which can show that any important exceptional condition currently exists).

The sequence of steps that happens is as follows:

* A plugin such as _lan_ detects that a service is unavailable.
* _systemHealth_ registers this in `environment/systemHealth`.
* _neoclock_ detects this and shows a moderately visible warning to the end user.
* The end user uses a web browser to visit `/systemHealth.html` to see what the problem is.
* The end user now has two options to make the visible warning go away:
	* Fix the problem.
	* Use one of the _ignore_ buttons. The error will subsequently still be recorded but it will not trigger the _neoclock_ visible warning for an hour or a day or so. 

Each service (device, sensor) has two fields that are
important. As an example, for service _internet_:

* `service/internet/errorMessage`: If this element exists and is non-empty it means the _internet_ service has an error condition (and that that condition is serious enough that we want to inform the user about it). The message will be copied into `environment/systemHealth/messages/internet`.
* `service/internet/ignoreErrorUntil`: If this value (timestamp) is set and is in the past it will be deleted. If it is in the future, the `errorMessage` field will not be copied into `environment/systemHealth`, effectively ignoring the error condition for some period of time.

## actions

The _systemHealth_ action triggers this plugin.