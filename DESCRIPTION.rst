Igor
====

Home Automation server. See <README.md>__ or <https://github.com/cwi-dis/igor> for details.

Prerequisites
-------------

You need to have Python v2.7 installed, and that should also have ``setuptools`` installed.

Installing Python's package installation program ``pip`` will also install ``setuptools``.

See also https://packaging.python.org/tutorials/installing-packages/

Installation
------------

Run:
	sudo python setup.py install
	
This installs the igor package, and command line utilities ``igorServer`` (the server),
``igorSetup`` (database administration), ``igorControl`` (server administration),
``igorVar`` (database access for shell scripts), and  ``igorCA`` (certificate admin)

Database configuration
----------------------

Create an initial database with:
	igorSetup initialize
	
If necessary populate it with plugins (with ``igorSetup addstd`` or ``igorSetup add``).
You will have to do a lot of manual editing of the ``~/.igor/database.xml``
file, for the time being.

Running
-------
Run:
	igorServer
and point your browser at <http://localhost:9333> or use ``igorControl``.

Make it run at system boot with ``sudo igorSetup runatboot`` or
``igorSetup runatlogin`` (OSX only).

