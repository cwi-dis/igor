# Igor, your personal IoT butler

Igor is named after the Discworld characters of the same name. 
You should think of it as a butler (or valet, or majordomo, 
I am not quite sure of the difference) that knows everything 
that goes on in your household, and makes sure everything runs smoothly. 
It performs its tasks without passing judgements and maintains complete 
discretion, even within the household. It can work together with other Igors 
(lending a hand) and with lesser servants such as [Iotsa-based devices](https://github.com/cwi-dis/iotsa).

Home page is <https://github.com/cwi-dis/igor>. 
This software is licensed under the [MIT license](LICENSE.txt) by the   CWI DIS group, <http://www.dis.cwi.nl>.

**Please note:** Igor is not a finished product yet, important functionality may be missing and/or faulty. Specifically, the security and privacy mechanisms are not complete yet.

## Prerequisites

You need to have Python 3.6 or later installed.
(Python 2.7 is also still supported but Python 3 is preferred).

You need the _pip_ package manager for the version of Python that you are going to use. Installing Python's package installation program _pip_ will also install _setuptools_.

Complete installation instructions are in [doc/using.md](doc/using.md).


## Technical description

Igor is basically a hierarchical data store, think of an XML file or a JSON 
file. There are three basic operations on the database:

- Plugin modules for sensing devices modify the database (for example 
recording a fact such as _"device with MAC address 12:34:56:78:9a:bc has 
obtained an IP address from the DHCP service"_). 
- Rules trigger on database 
changes and modify other entries in the database (for example _"if device 
12:34:56:78:9a:bc is available then Jack is home"_ or _"If Jack is home 
the TV should be on"_). 
- Action plugins also trigger on database changes and 
allow control over external hardware or software (for example _"If the TV 
should be on emit code 0001 to the infrared emitter in the living room"_).

## Comparison to other IoT solutions

Igor can be completely self-contained, it is not dependent on any cloud 
infrastructure. This means your thermostat should continue controlling your 
central heating even if the Google servers are down. Moreover, Igor allows 
you to keep information in-house, so you get to decide which information 
you share with whom (so you do not have to share your room temparature
with Google if you do not want to). That said, Igor can work together with cloud services, 
so you can use devices for which vendor-based cloud use is the only option, 
but at least _you_ get to combine this information with other sensor data.

Igor is primarily state-based, unlike ITTT (If This Then That) and many other 
IoT platforms which are primarily event-based. The advantage of state-based 
is that it allows you to abstract information more easily. In the example of 
the previous section, if you later decide to detect _"Jack is home"_ with a 
different method this does not affect the other rules. Moreover, you can 
give a person (or service) access to the state variable _"Jack is home"_ 
without giving them the MAC address of his phone.

## Server Implementation

Igor is implemented in Python (2 or 3). At the core of Igor is an XML datastore (using
``xml.dom``, so the underlying datastore can be replaced by a more efficient 
one if needed) with locking for concurrent access. Only elements (and text data)
are used for normal storage, no attributes, so the data structures can easily 
be represented in JSON or some other form.

On top of that an XPath 1.0 implementation (currently ``py-dom-xpath`` but again: could be replaced for efficiency reasons) to allow searching, selecting and combining (using expressions) of database elements.

On top of that is a webserver (based on [Flask](http://flask.pocoo.org), using either _http_ or _https_ access) that allows REST-like access to the database (GET, PUT, POST and DELETE methods), by default on port 9333. The server handles conversion between the internal (XML) format and external XML, JSON or plain text format.

In addition to database access, the web server exposes internal
functionality (for example to save the database), more general XPath
expressions over the database and plugin modules. It can also serve static
content and template-based content (using the web.py template functionality
and data from the database).

Then there is an ``actions`` module, populated from a special section of the
database, that allows actions to be triggered by events. Here, _actions_ are
REST operations (on the database itself or on external URLs) using data constructed from the database, and _events_ are one or a combination of:

- periodic timers,
- specific incoming REST requests,
- changes to database nodes that match specific XPath selectors.

Igor has an optional capability-based access control mechanism that allows fine-grained control over which agent (user, external device, plugin, etc) is allowed  to do which operation. Human users can log in to the Igor server to gain access to their set of capabilities, external devices can carry their capabilities in requests. Igor can handle signing those capabilities with a secret key shared between the device and Igor.

For convenience on a local subnet Igor can also function as a Certificate Authority (CA), signing the SSL certificates needed to allow trusted _https_ access between Igor and external devices (and any other local services you have).

There are a number of command-line utilities and Python modules, such as ``igorVar`` to allow access to the database REST interface from shell scripts, ``igorSetup`` to initialize and control the database or ``igorCA`` to access the Certificate Authority.

## Plugins

A number of plugins is included. Some of these are generally useful, some should be considered example code to help you develop your own plugins. See [igor/std-plugins/readme.md](igor/std-plugins/readme.md) for a description of the standard plugins.

## Helpers

Some of the plugins come with helper utilities or servers. See [helpers/readme.md](helpers/readme.md) for
details.

## REST entry points

The entry points into Igor are described in [doc/rest.md](doc/rest.md).
## Schema

A description of the database can be found in [doc/schema.md](doc/schema.md).

## Missing functionality

Mirroring and distributing the database over multiple Igor instances is planned but not implemented yet.

A method for easy installation (and updating and removal) of externally supplied plugins is not implemented yet.

a more user-friendly method of editing the database is not implemented yet.


## Building and installing Igor

See [doc/using.md](doc/using.md).

## Configuring and running Igor

See [doc/using.md](doc/using.md).

