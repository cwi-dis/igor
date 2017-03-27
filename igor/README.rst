Igor
====

Home Automation server. More details to be provided.

Installation
------------

Most of the work is done by running::
	sudo python setup.py install
but possibly ``py-dom-xpath`` will not install automatically, in that case search
for it in pypi.python.org and install it first.

This should also install scripts igorServer (to start the server) and igorVar
(command line interface to access the database).

Configuration (Linux)
---------------------

To run at startup:
- edit initscript-igor, modify path, database, etc
- ``sudo cp initscript-igor /etc/init.d/igor``
- ``sudo update-rc.d igor defaults``
- Reboot, or ``sudo service igor start``

You may also want to install dependencies such as *bleServer* (or remove them).

Configuration (OSX)
-------------------

To run at login:
- edit nl.cwi.dis.igor.plist, modify paths, database, etc.
- ``cp nl.cwi.dis.igor.plist ~/Library/LaunchAgents/``
- ``launchctl load ~/Library/LaunchAgents/nl.cwi.dis.igor.plist``

(running at startup may work by copying into /Library/LaunchDaemons but has not been
tested yet).

Running
-------

To be provided
