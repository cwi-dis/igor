# _fitbit - get health data from fitbit cloud service

Retrieves health data from Fitbit devices using the Fitbit cloud API and stores this in `sensors/_fitbit`.

It is an example of a plugin using OAuth2 to retreive data from a web service.

It has an underscore before its name because otherwise there would be a name clash with the underlying Python module that is used to obtain the Fitbit data (sigh).

## requirements

You should own a [Fitbit](http://www/fitbit.com) device. Only the Fitbit Aria scale has been tested.

Visit the page `/plugin/_fitbit/page/setup.html` to register your instance of Igor with the _fitbit.com_ cloud API.

### Manual registration

If the _setup.html_ page does not work you can do manual setup. You should register your Igor as an application at <https://dev.fitbit.com/apps/new>. You will probably have to register yourself
as a Fitbit developer before you can do this. There is one parameter that you need to specify on the registration page that is
crucial you get right: the _Callback URL_. This is where an Igor user is redirected to after giving permission and must be correct.
If your Igor runs on `igor.local` port `9333` the URL you must use is `http://igor.local:9333/plugin/_fitbit/auth2`.

The fitbit registration of your application gives you a `client_id_` and `client_secret` that you enter into the plugin data and that identify
your Igor to Fitbit.

## per-user requirements

For each Fitbit user that is also an Igor user visit the _setup.html_ page and create the per-user entry. Then add the _action_ (see below) to pull data for that user into Igor.

### Manual user setup

For each Fitbit user _yournamehere_ you first create empty entries `sensors/fitbit/yournamehere` and `identities/yournamehere/plugindata/_fitbit`.

You now take the following steps to give Igor permission to fetch your data:

- You use a normal browser to visit <http://igor.local:9333/plugin/_fitbit/auth1?user=yournamehere>. 
- Your browser will be redirected to the Fitbit website, where you are asked for permission to give Igor access to your health data. You log in with your Fitbit username and
password and give permission.
- Your browser will be redirected back to Igor, to the _Callback URL_ specified previously, with some secret data.
- Igor will contact the Fitbit website with the secret data to obtain your access tokens.
- These access tokens are stored in `identities/yournamehere/plugindata/_fitbit`.

If all this worked Igor can now get the health data for _yournamehere_. You can add the _action_ to fetch the data regularly.

## plugin entrypoints

- `/plugin/_fitbit?user=yournamehere` Obtain health data for user _yournamehere_, refreshing the access tokens as needed. Optional parameters:
	- `methods` a comma-separated list of methods to call (default: `get_bodyweight`). See [Python Fitbit documentation](https://python-fitbit.readthedocs.io) for the details.
	- All other keyword arguments are passed to each of the methods in turn.
- `/plugin/_fitbit/auth1?user=yournamehere` Start the authentication process for user _yournamehere_ to enable Igor to obtain the health data.
- `/plugin/_fitbit/auth2?code=...&state=yournamehere` Second step in the authentication process, called through browser redirection by Fitbit.
- `/plugin/_fitbit/settings` and `/plugin/_fitbit/userSettings` are internal calls to implement the actions in _setup.html_.

## schema

* `plugindata/_fitbit` Identity of this Igor for the Fitbit cloud service:
	* `client_id` the identity of your application (Igor)
	* `client_secret` the password of your application (Igor)
	* `system` Should be `en_GB` for imperial values, and (for example) `nl_NL` for metric.
* `identities/_yournamehere_/plugindata/_fitbit` Fitbit access data for person _yournamehere_:
	* `token` Fitbit token. Most important fields are `refresh_token` and `access_token`.
	* `methods`, `resource`, `period` and other keyword arguments can be specified, these will be used as defaults when `/plugin/_fitbit` is called for this user.
* `sensors/fitbit/_yournamehere_` Fitbit measurements for person _yournamehere_:
	* `body-weight` Weight data time series:
		* `value` The value of this measurement
		* `dateTime` For which date the value is.
	* ...
	
## actions

One for each user for which Igor needs to fetch Fitbit health data:

```
<action>
	<interval>36000</interval>
	<url>/plugin/_fitbit?user=yournamehere</url>
	<representing>sensors/_fitbit</representing>
</action>

```
