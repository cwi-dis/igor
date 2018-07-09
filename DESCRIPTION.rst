Igor
====

Home Automation server. See <README.md>__ or <https://github.com/cwi-dis/igor> for details.

Installation
------------

Run:
	sudo python setup.py install
	
This installs the igor package, and command line utilities ``igor`` (the server),
``igorSetup`` (database administration), ``igorControl`` (server administration)
and ``igorVar`` (database access for shell scripts).

Database configuration
----------------------

Create an initial database with:
	igorSetup initialize
	
Then populate it with plugins (with ``igorSetup addstd`` or ``igorSetup add``).
You will have to do a lot of manual editing of the ``~/.igor/database.xml``
file, for the time being.

Running
-------
Run:
	igor
and point your browser at <http://localhost:9333> or use ``igorControl``.

Make it run at system boot with ``sudo igorSetup runatboot`` or
``igorSetup runatlogin`` (OSX only).

