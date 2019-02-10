# Rest entry points

The Igor HTTP or HTTPS server has the following REST entrypoints:

## /data/**
Accesses data elements. GET, PUT, POST and DELETE allowed. The argument is technically an XPath expression that should resolve to a single element (but see below). Data can be provided with mimetypes `application/xml`, `application/json` or `text/plain`.

Query parameters:
* `.VARIANT` can be used to get data slightly different:
  * `multi` to get allow getting multiple elements (normally multiple elements matching the expression is considered an error, except for `text/plain` when the values are concatenated)
  * `raw` will also include namespaced elements and attributes. These are used for internal administration and usually not returned.
  * `multiraw` combines `multi` and `raw` behaviour.
  * `ref` to get an XPath for the resulting objects.
* `.METHOD` convenience parameter for debugging with the browser. a `GET` request with `.METHOD=DELETE` will do a `DELETE` operation.

## /evaluate/**

Evaluate an XPath expression that can return any XPath expression value. `GET` only.

## /*

Get static or template web pages or other files. `GET` only. Returns static data from the `static` directory or an interpolated Jinja2 template from the `template` directory. Parameters are passed to the template.

## /action/\*

Trigger a named action. `GET` only.

## /action/\*/\*

Trigger a named plugin action. `GET` only. The first field is the plugin name. The second field is the action name, which is looked up in `/data/plugindata/pluginname`.

## /plugin/\*[/*]

Run a plugin. `GET` only. First field is the plugin name, optional second field is the method of the plugin to call (default _index_). Query parameters are passed to the Python method as named arguments. Plugin data from `/data/plugindata/_name_` is made available to the plugin factory function, and if a _user_ query parameter is present Igor will add a _userData_ argument containing the data from `/data/identities/_user_/plugindata/_name_` (as a Python dictionary).

## /plugin/\*/page/\*.html

Retrieve a plugin UI (user interface) page. The template page is looked up inside the plugin directory and rendered through Jinja2. Query parameters are passed to the template. Plugin data is available as above.

## /plugin/\*/script/\*

Run a plugin script. `GET` only. First argument is the plugin name, second argument is the script name. The script is obtained from file `/plugins/_name_/scripts/_scriptname_.sh`.

query parameters are passed to the script as environment variables, with `igor_` prepended to the query parameter name. Per-plugin data and optional per-user data (as for `/plugin`) is combined into an `igor_pluginData` environment variable with has all the data in JSON encoded form.
The plugin script has access to the plugin capability set, valid for a single call to the database (through `igorVar`) via a one-time-password mechanism.

## /login

Helper for logging in and out with a browser session.

## /internal/\*[/\*]

Helper for running internal commands such as _save_,  _restart_ or _updateStatus_.