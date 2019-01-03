
Plugin implementation
=====================

Igor comes with a set of standard plugins. Some of these can be used as-is, and installed using (for example):

.. code-block:: sh

   igorSetup addstd copytree

Some are more examples that you should copy and adapt to your own need, or use as inspiration. 

Plugins take their name (for use in ``plugindata``\ , for example) from the name they are installed under. So you can install multiple independent copies (for example as *say* and *sayInBedroom*\ ) and use different plugindata to control each copy of the plugin.

Various plugins should be considered standard to Igor operations and usually installed:


* *ca* allows access to the Certificate Authority
* *device* allows adding and removing devices
* *user* allows adding and removing users
* *systemHealth* implements the self-checks and health-checks of Igor

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

Each operation will call a method on the object. There will always be an argument ``token`` which will be the current set of capabilities (or ``None`` if Igor is running without capability support) and which the plugin will have to pass to most Igor API calls.

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

The fragment overlay installation may be delayed until the next time the Igor server is restarted.

It may be necessary to do some hand editing of the database after installing, because you may have to modify some elements (such as hostname fields) and you may need to duplicate some (with modifications) for example if you want the *lan* plugin to test different services.

\*.html
^^^^^^^

A plugin can contain a user interface through HTML pages. These are accessed with URLs ``/plugin/_pluginname_/page/_pagename_.html``. Actually, these are `Jinja2 <http://jinja.pocoo.org>`_ templates. Within the template you have access to the following variables:


* *pluginName* is the name under which the plugin has been installed.
* *pluginObject* the plugin object (if the plugin has an ``igorplugin.py`` Python module).
* *token* is the capability of the current user (the user visiting the page).
* *pluginData* is the internal data of the plugin (from ``/data/plugindata``\ ).
* *user* is the current user (if logged in).
* *userData* is the per-plugin data for the current user (if logged in).
* all url parameters.

In general, the template should provide forms and such to allow the user to change settings, and then call methods in the plugin proper to implement those changes (because the plugin will run with a *token* that allows read/write access to the plugin data).
