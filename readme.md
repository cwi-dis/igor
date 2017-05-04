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

## Implementation

Igor is implemented in Python 2. At the core of Igor is an XML datastore (using
``xml.dom``, so the underlying datastore can be replaced by a more efficient 
one if needed) with locking for concurrent access. Only elements (and text data)
are used for normal storage, no attributes, so the data structures can easily 
be represented in JSON or some other form.

On top of that an XPath 1.0 implementation (currently ``py-dom-xpath`` but again: 
could be replaced for efficiency reasons) to allow 
searching, selecting and combining (using expressions) of database elements.

On top of that is a webserver (based on ``web.py``) that allows REST-like 
access to the database (GET, PUT, POST and DELETE methods). The server handles 
conversion between the internal (XML) format and external XML, JSON or plain text format.
In addition to database access, the web server exposes internal
functionality (for example to save the database), more general XPath
expressions over the database and plugin modules. It can also serve static
content and template-based content (using the web.py template functionality
and data from the database).

Finally there is an ``actions`` module, populated from a special section of the
database, that allows actions to be triggered by events. Here, _actions_ are
REST operations (on the database itself or on external URLs) using data constructed
from the database, and _events_ are one or a combination of:

- periodic timers,
- specific incoming REST requests,
- changes to database nodes that match specific XPath selectors.

There is a command-line utility ``igorVar.py`` to allow access to the database REST
interface from shell scripts.

## Plugins

A number of plugins is included. Some of these are generally useful, some should be considered
example code to help you develop your own plugins. See [igor/plugins/readme.md](igor/plugins/readme.md) for a description of the plugins.

## Helpers

Some of the plugins come with helper utilities or servers. See [helpers/readme.md](helpers/readme.md) for
details.

## Schema

A description of the database can be found in [schema.md](schema.md).

## Missing functionality

A security and access control module is planned but not implemented yet.

Mirroring and distributing the database over multiple Igor instances is planned but
not implemented yet.

A method for easy installation (and updating and removal) of plugins is not implemented yet.

a more user-friendly method of editing the database is not implemented yet.


## Building and installing

See [DESCRIPTION.rst](DESCRIPTION.rst) for now.

## Configuring the database

See [DESCRIPTION.rst](DESCRIPTION.rst) for now.

## Configuring for automatic execution

See [DESCRIPTION.rst](DESCRIPTION.rst) for now.
