homeServer
==========

Home Automation server. More details to be provided.

Installation
------------

Most of the work is done by running::
	sudo python setup.py install
but possibly ``py-dom-xpath`` will not install automatically, in that case search
for it in pypi.python.org and install it first.

Configuration
-------------

To run at startup:
- edit initscript-homeServer, modify path, database, etc
- ``sudo cp initscript-homeServer /etc/init.d/homeServer``
- ``sudo update-rc.d homeServer defaults``
- Reboot, or ``sudo homeServer start``

The init script current requires *screen*, install with ``apt-get``.
You may also want to install dependencies such as *bleServer* (or remove them).

Running
-------

To be provided
