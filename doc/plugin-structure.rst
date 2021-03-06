
Plugin implementation
=====================

The description here is probably not complete enough yet. Examine some of the standard
plugins to see how things work. Some good examples plugins:

* *say* is a simple output-only plugin that uses shell commands to drive a speech synthesizer.
* *lan* uses Python sockets and *requests* to check whether services are available.
* *iotsaDiscovery* is a plugin with an elaborate user interface and a good example of the Jinja HTML templates working together with the Python plugin code.
* *fitbit* obtains data for one or more users from an external cloud service, and uses the three-way *OAuth2* handshake to authenticate to that service.

Plugin Structure
----------------

A plugin generally contains either a Python module or a set of scripts (or both) to communicate with an external device or service. In addition a plugin can contain user-interface pages to allow the user to configure or operate the plugin (or the device it controls).

igorplugin.py
^^^^^^^^^^^^^

A plugin can be implemented in Python. Then it must define a class (or factory function)

.. code-block:: python

   igorPlugin(igor, pluginName, pluginData)

which is called whenever any method of the plugin is to be called. This function should return an object on which the individual methods are looked up. The ``igorPlugin`` function is called every time a plugin method needs to be called, but it can of course return a singleton object. See the *watchdog* plugin for an example. *igor* is a pointer to the global Igor object (see below), *PluginName*
is the name under which the plugin has been installed, and *PluginData* is filled from ``/data/plugindata/_pluginname_``. 

Each operation will call a method on the object. There will always be an argument ``token`` which will be the current full set of capabilities (or ``None`` if Igor is running without capability support) and which the plugin will have to pass to most Igor API calls.
The full set of capabilities consists of the capabilities carried by the caller of this plugin *plus* the capabilities of the plugin itself. There is another argument ``callerToken`` which contains only the capabilities of the caller.
The intention of these two sets of capabilities is that the plugin code will use the *token* set when accessing private data and *callerToken* when accessing data that is passed in by the user (or when it wants to ensure
the calling user actually has the right to access the data).

Accessing ``/plugin/pluginname`` will call the ``index()`` method. 

Accessing ``/plugin/pluginname/methodname`` will call ``methodname()``.  

The methods are called with ``**kwargs`` encoding the plugin arguments, and if there is a ``user`` argument there will be an additional argument ``userData`` which is filled from ``/data/identities/_user_/plugindata/_pluginname_``.

Methods starting with an underscore ``_`` are not callable through the web interface but can be called by the plugin template pages or by other plugins.

The *igor* object has a number of attributes that allow access to various aspects of Igor:


* ``igor.database`` is the XML database (implemented in ``igor.xmlDatabase.DBImpl``\ )
* ``igor.databaseAccessor`` is a higher level, more REST-like interface to the database.
* ``igor.internal`` gives access to the set of commands implemented by ``igor.__main__.IgorInternal``.
* ``igor.app`` is the web application (from ``igor.webApp.WebApp``\ ).
* ``igor.plugins`` is the plugin manager.

scripts
^^^^^^^

A plugin can be (partially) implemented with shell scripts. Accessing ``/pluginscript/pluginname/scriptname`` will try to run ``pluginname/scripts/scriptname.sh``.

Scripts get an environment variable ``IGORSERVER_URL`` set correctly so they can use the *igorVar* command easily.

Each argument is passed to the script (in Python notation) with ``igor_`` prepended to the name. ``igor_pluginName`` contains the name under which the plugin is installed.

The per-plugin data from ``/data/plugindata/_pluginname_`` and (if the *user* argument is present) the per-user per-plugin data from ``/data/identities/_user_/plugindata/_pluginname_``
is encoded as a Python dictionary and passed in the ``igor_pluginData`` environment variable.

database-fragment.xml
^^^^^^^^^^^^^^^^^^^^^

Many plugins require plugin-specific data in the database. Often there are one or more of the following items:


* plugin-specific actions that are needed to actually fire the plugin,
* plugin settings, for example to tell which host a specific device is connected to,
* boilerplate entries for where the plugin will store its data.

Usually these entries are explained in the plugin readme file, in the *schema* section.

Usually there is a file ``database-fragment.xml`` that show the entries needed. Basically this file is the minimal set of elements that should be in the database for the plugin to function. 

This database fragment is overlayed onto the database when installing the plugin. Every occurrence of the exact string ``{plugin}`` is replaced by the name of the plugin before installing into the database.

	*Note*: this looks somewhat like a Jinja construct but it is not, for the current release. Simple text substitution is used.

The fragment overlay installation may be delayed until the next time the Igor server is restarted.

It may be necessary to do some hand editing of the database after installing, because you may have to modify some elements (such as hostname fields) and you may need to duplicate some (with modifications) for example if you want the *lan* plugin to test different services.

\*.html
^^^^^^^

A plugin can contain a user interface through HTML pages. These are accessed with URLs ``/plugin/_pluginname_/page/_pagename_.html``. Actually, these are `Jinja2 <http://jinja.pocoo.org>`_ templates. Within the template you have access to the following variables:


* *pluginName* is the name under which the plugin has been installed.
* *pluginObject* the plugin object (if the plugin has an ``igorplugin.py`` Python module).
* *callerToken* is the capability of the current user (the user visiting the page).
* *token* is the capability of the current user (the user visiting the page) plus the capability owned by the plugin itself.
* *pluginData* is the internal data of the plugin (from ``/data/plugindata``\ ).
* *igor* is the toplevel Igor object.
* *user* is the current user (if logged in).
* *userData* is the per-plugin data for the current user (if logged in).
* all url parameters.

	*Note*: the availability of the *igor* object means that a plugin has rather unlimited power, and can probably run any command
	and access any file that the userID under which Igor is executing can access. This is a security issue, and you should never install
	plugins from sources you do not trust. This will be addressed in a future release.

In general, the template should provide forms and such to allow the user to change settings, and then call methods in the plugin proper to implement those changes (because the plugin will run with a *token* that allows read/write access to the plugin data). 
If methods are intended to be called solely from templates and never directly through the REST interface you should start the methodname with an underscore.

The plugin decides whether to use *token* or *callerToken* to access data depending on whether it is accessing data on behalf of itself (then it uses *token*) or on behalf of the person visiting the web page (in which case it uses *callerToken*).

Plugins can access other plugins through the ``igor.plugins`` object.
