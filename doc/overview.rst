
Igor, your personal IoT butler
==============================

Igor is named after the Discworld characters of the same name. You should
think of it as a butler (or valet, or majordomo, I am not quite sure of the
difference) that knows everything that goes on in your household, and makes
sure everything runs smoothly. It performs its tasks without passing
judgements and maintains complete discretion, even within the household. It
can work together with other Igors (lending a hand) and with lesser servants
such as `Iotsa-based devices <https://github.com/cwi-dis/iotsa>`_.

Home page is https://github.com/cwi-dis/igor. This software is licensed
under the `MIT license <LICENSE.txt>`_ by the   CWI DIS group,
http://www.dis.cwi.nl.

What Igor does
--------------

Igor performs its tasks of managing your household by knowing three things:

* what is going on at the moment,
* what needs to happen when, and
* how to make that happen.

For a freshly-installed Igor all of these three categories are pretty much
empty, so basically Igor sits there doing nothing.

But then you can add plugins for sensors that allow Igor to get an understanding
of what is going on: environmental sensors help it determining the indoor temperature,
but also probes to test whether your internet connection is working or which
personal devices (mobile phones) are currently connected to the local WiFi network.

Next you can add plugins for controlling devices: turning on or off electrical
appliances, lights, music, etc.

Finally you add rules to explain to Igor what needs to happen when. Igor can now
ensure that there is music playing between 08.00 and 09.00 on weekdays, but only
if there are people at home.


Technical description
---------------------

Igor is basically a hierarchical data store, think of an XML file or a JSON 
file. There are three basic operating agents on the database:


* Plugin modules for sensing devices modify the database (for example 
  recording a fact such as *"device with MAC address 12:34:56:78:9a:bc has 
  obtained an IP address from the DHCP service"*\ ). 
* Rules trigger on database 
  changes and modify other entries in the database (for example *"if device 
  12:34:56:78:9a:bc is available then Jack is home"* or *"If Jack is home 
  the TV should be on"*\ ). 
* Action plugins also trigger on database changes and 
  allow control over external hardware or software (for example *"If the TV 
  should be on emit code 0001 from the infrared emitter in the living room"*\ ).

Comparison to other IoT solutions
---------------------------------

Igor can be completely self-contained, it is not dependent on any cloud
infrastructure. This means your thermostat should continue controlling your
central heating even if the Google servers are down. Moreover, Igor allows
you to keep information in-house, so you get to decide which information you
share with whom (so you do not have to share your room temparature with
Google if you do not want to). That said, Igor can work together with cloud
services, so you can use devices for which vendor-based cloud use is the
only option, but at least *you* get to combine this information with other
sensor data.

Igor is primarily state-based, unlike ITTT (If This Then That) and many other 
IoT platforms which are primarily event-based. The advantage of state-based 
is that it allows you to abstract information more easily. In the example of 
the previous section, if you later decide to detect *"Jack is home"* with a 
different method this does not affect the other rules.

Igor has a fine-grained access control mechanism, unlike most (all?) other
IoT solutions. This makes it possible to give some people (or automatic
agents) access to high-level abstracted information without giving them
access to the low-level information that causes Igor to known this
high-level information. In the example from the previous paragraph, you can
give a person (or service) access to the state variable *"Jack is home"*
without giving them the MAC address of his phone.

Usage
-----

After initial installation Igor will usually be started at system boot time
on some machine in the household that has access to the network and that is
always on. A Raspberry PI sitting somewhere in a corner is an option, but any
MacOSX or Linux machine can be used.

Igor then presents a user interface at port 9333. So if the hostname of the
machine Igor is running on is *igor.local* you can access this user interface
by browsing to <https://igor.local:9333/>.

The user interface allows you to inspect all items in the Igor database
that are considered fully accessible, in other words: all information about
your household that you consider to be available to anyone.

You can also log in. Initially Igor knows about a single user, *admin*, with
no password. You can add a password (you should). When logged in you can
access more information, besically everything in the database for the
*admin* user. You can then add accounts for other users, such as yourself
and probably for all other people in the family. You can grant specific
rights (access permissions) to different users. 

In the user interface you can then add devices, sensors and other plugins (for
example to determine the health of your internet connection, or whether backups
of important machines are up-to-date). You can also modify access control
rules, examine the Igor log file, etc.

In addition various plugins have their own user interface allowing you to control
them or to inspect their current status.

	**Note**: there are two common operations that can currently *not* be done through
	the user interface, at least not easily:
	
	* Modifying individual data items,
	* Adding (or changing or deleting) action rules.
	
	This expected to be addresed in a future release. In the mean time you
	either have to use the command line tools or stop Igor and edit the XML
	database manually.
	
There are also some command line tools that are meant primarily for use in
shell scripts but can also be used to manually control Igor.

Implementation overview
-----------------------

Igor is implemented in Python (2 or 3). At the core of Igor is an XML
datastore (using ``xml.dom``\ , so the underlying datastore can be replaced
by a more efficient one if needed) with locking for concurrent access. Only
elements (and text data) are used for normal storage, no attributes, so the
data structures can easily be represented in JSON or some other form.

On top of that an XPath 1.0 implementation (currently ``py-dom-xpath`` but
again: could be replaced for efficiency reasons) to allow searching,
selecting and combining (using expressions) of database elements.

On top of that is a webserver (based on `Flask <http://flask.pocoo.org>`_\ ,
using either *http* or *https* access) that allows REST-like access to the
database (GET, PUT, POST and DELETE methods), by default on port 9333. The
server handles conversion between the internal (XML) format and external
XML, JSON or plain text format.

In addition to database access, the web server exposes internal
functionality (for example to save the database), more general XPath
expressions over the database. It can also serve static content and
template-based content (using the `Jinja2
<http://jinja.pocoo.org/docs/2.10/>`_ template engine and data from the
database).

Plugins
^^^^^^^

There is a plugin mechanism that allows adding plugins that can control
external devices based on variables in the database changing. Or they can
change database variables to reflect the state of external devices. Or both.

A number of plugins is included. Some of these are generally useful, some
should be considered example code to help you develop your own plugins. See
`igor/std-plugins/readme.md <igor/std-plugins/readme.md>`_ for a description
of the plugin architecture and the standard plugins.

Some of the plugins come with helper utilities or servers. See
`helpers/readme.md <helpers/readme.md>`_ for details.


Actions
^^^^^^^

Then there is an ``actions`` module, populated from a special section of the
database, that allows actions to be triggered by events. Here, *actions* are
REST operations (on the database itself or on external URLs) using data
constructed from the database, and *events* are one or a combination of:


* periodic timers,
* specific incoming REST requests,
* changes to database nodes that match specific XPath selectors.

Security and privacy
^^^^^^^^^^^^^^^^^^^^

Igor has an optional capability-based access control mechanism that allows
fine-grained control over which agent (user, external device, plugin, etc)
is allowed  to do which operation. Human users can log in to the Igor server
to gain access to their set of capabilities, external devices can carry
their capabilities in requests. Igor can handle signing those capabilities
with a secret key shared between the device and Igor.

For convenience on a local subnet Igor can also function as a Certificate
Authority (CA), signing the SSL certificates needed to allow trusted *https*
access between Igor and external devices (and any other local services you
have).

External interfaces
^^^^^^^^^^^^^^^^^^^

There are a number of command-line utilities and Python modules, such as
``igorVar`` to allow access to the database REST interface from shell
scripts, ``igorSetup`` to initialize and control the database or ``igorCA``
to access the Certificate Authority.

And of course there is the main REST interface.


Missing functionality
^^^^^^^^^^^^^^^^^^^^^

The user interface is currently not very logically organized, and it is 
completely unstyled and ugly.

There is no friendly user interface yet to manually modify the database.

There is no friendly user interface yet to modify actions.

Mirroring and distributing the database over multiple Igor instances is
planned but not implemented yet.

A method for easy installation (and updating and removal) of externally
supplied plugins is not implemented yet.


