
Using Igor
==========

Prerequisites
-------------

You need to have Python 3.6 or later installed.
(Python 2.7 is also still supported but Python 3 is preferred).

You need *pip* and *setuptools* (if not already included in your Python installation). Installing Python's package installation program *pip* will also install *setuptools*.

Your system might well have both Python 2.7 and Python 3.X installed, for that reason it is best to always use the commands ``python3`` and ``pip3`` (as opposed to ``python`` and ``pip``\ , which could refer to 2 or 3 depending on circumstances).

See also https://packaging.python.org/tutorials/installing-packages/.

Installing the software
-----------------------

Download the source via https://github.com/cwi-dis/igor. 

.. code-block:: sh

   git clone https://github.com/cwi-dis/igor

Then change into the ``igor`` directory, and install with

.. code-block:: sh

   sudo pip3 install -r requirements.txt
   python3 setup.py build
   sudo python3 setup.py install

This installs the main binary ``igorServer`` and the utilties ``igorVar``\ , ``igorSetup``\ , ``igorControl`` and ``igorCA``.

The instructions above, using ``sudo`` for installation, will install Igor and the required dependencies for all users on your system. Installing for the current user only may be possible but is untested.

You may also want to install some of the helper utilities from the ``helpers`` subdirectory.

Setup the database
------------------

Create an initial empty database with

.. code-block:: sh

   igorSetup initialize

The default database is stored in ``~/.igor``.  Currently, Igor databases are *not* compatible between versions, so if you have used an older version of Igor you should first remove the old database.

Next add the standard plugins:

.. code-block:: sh

   igorSetup addstd lan systemHealth ca user device

(these are the standard plugins used by the default database, which as distributed do little more than check the health of your internet connection).

You should now be able to run the server with

.. code-block:: sh

   igorServer

and point your browser at http://localhost:9333 to see Igor in action.

At any time the server is not running you can check the consistency of the database, with

.. code-block:: sh

   igorServer --check

or alternatively you can try to automatically fix it with

.. code-block:: sh

   igorServer --fix

Testing the software (optional)
-------------------------------

There is a unittest-based test suite in the ``test`` subdirectory. The easiest way to run the tests is to first install the software (as per the instructions above) and then run

.. code-block:: sh

   python3 setup.py test

This will run all tests in various configurations (with and without https support, with and without capability support, etc). This will run the tests in complete isolation, using a separate temporary install and separate Igor instances running on different ports, etc. So it will not interfere with your installed igor.

If you want more control (for example to specify test options and such) you can in stead use the following command line (which will use the Igor version installed on your system): 

.. code-block:: sh

   python3 -m test.test_igor

It is also possible to test the performance of Igor (again with the various configurations):

.. code-block:: sh

   python3 -m test.perf_igor

will run a set of actions similar to the unittests (for a minimum number of calls and a minimum duration) and report number of calls, average runtime per call and standard deviation of the runtimes.

Updating the software
---------------------

Stop the server if necessary:

.. code-block:: sh

   igorControl -u http://localhost:9333 stop

In the ``igor`` directory, do

.. code-block:: sh

   git pull

and repeat the three steps from earlier:

.. code-block:: sh

   sudo pip3 install -r requirements.txt
   python3 setup.py build
   sudo python3 setup.py install

Restart the server:

.. code-block:: sh

   igorServer

Security
--------

It is advisable to run Igor with the secure *https* protocol as opposed to the completely open *http* protocol. Igor can use any SSL certificate, but simplest is to use a self-signed certificate or to configure Igor as a Certificate Authority.

Igor as a CA
^^^^^^^^^^^^

Enabling Igor as a Certificate Authority is the best option if there are other services (such as `Iotsa <https://github.com/cwi-dis/iotsa>`_\ -based devices, or other Igors) that you want to protect with *https*. Details on using Igor as a CA are in `../igor/std-plugins/ca/readmd.md <../igor/std-plugins/ca/readme.md>`_ but here are the commands needed to get this kickstarted:

.. code-block:: sh

   igorCA initialize
   igorCA self igor.local localhost 127.0.0.1 ::1

The ``self`` command should be given all hostnames and IP addresses via which you expect to access Igor, and the "canonical name" should be first.

Self-signed Certificate
^^^^^^^^^^^^^^^^^^^^^^^

Alternatively, to use a self-signed certificate for Igor, run

.. code-block:: sh

   igorSetup certificate

And restart Igor. Igor will detect that it has a certificate and start up in secure mode.

Now connect your browser to https://localhost:9333. You will get a number of warnings about an untrusted website (because you used a self-signed certificate), read these and select all the answers that indicate you trust this website. This needs to be done only once (per browser).

Capability-based access control
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Igor has support for experimental fine grained access control, using capabilities. On top of that there is user-based (login) access control.

This feature is incomplete, especially the documentation is lacking, therefore it is not enabled by default. If you want to experiment you can use first

.. code-block:: sh

   igorServer --capabilities --fix

to add the required set of minimal capabilities to your database, and then run

.. code-block:: sh

   igorServer --capabilities

to run your server in capability-based acess control mode. You will probably need various visits to the */users.html*\ , */devices.html* and */capabilities.html* administrative interfaces to get anything to work.

It is also possible to let Igor go through all the motions of capability-based access control, but allowing the operations even if the capabilities would disallow it. This can be handy while converting your database to use capabilities: you will get all the error messages about missing capabilities, but as warnings only. Therefore your Igor server will function as if no capabilities were in use. Enable this mode with

.. code-block:: sh

   igorServer --warnCapabilities

Igor configuration
------------------

You will need to configure your Igor to do something useful. On the Igor landing page there are links to pages that allow you to add *devices*\ , *plugins* and *users*. However, this functionality is currently incomplete, so various things will have to be configured manually.

Manual configuration
^^^^^^^^^^^^^^^^^^^^

See `../igor/std-plugins/readmd.md <../igor/std-plugins/readme.md>`_ for a list of useful plugins that are included with Igor, and `schema.md <schema.md>`_ for how to add useful actions to your database.

Stop Igor before editing your ``~/.igor/database.xml`` in a text editor. The following command helps you with this:

.. code-block:: sh

   igorSetup edit

Starting automatically
----------------------

Igor can be started automatically at system boot with the following command:

.. code-block:: sh

   igorSetup runatboot

Command line utilities
----------------------

igorSetup
^^^^^^^^^

Utility to help with configuring Igor. This utility has to be run on the same computer as *igorServer* runs on. Various subcommands were explained in the previous section, calling ``igorSetup`` without arguments will give concise help on the available subcommands.

igorControl
^^^^^^^^^^^

Runtime control over Igor: stopping the service, saving the database, etc.

Uses the *http[s]* interface so can be run on a different computer. Configuration parameters can be obtained from ``~/.igor/igor.cfg`` or environment variables, see below.

``igorControl help`` should list the available commands.

igorVar
^^^^^^^

Accesses the database to read or write variables.

Uses the *http[s]* interface so can be run on a different computer. Configuration parameters can be obtained from ``~/.igor/igor.cfg`` or environment variables, see below.

``igorVar --help`` explains the parameters.

The *igorVar* utility can also be used to communicate with other services that have a REST-like interface and use JSON or XML as data format.

igorCA
^^^^^^

Certificate Authority command line tool. Call ``igorCA help`` for a list of commands. More detail (a little more:-) can be found in `../igor/std-plugins/ca/readmd.md <../igor/std-plugins/ca/readme.md>`_.

Supporting modules
------------------

The command line tools listed above also do double duty as importable Python modules, enabling accessing Igor from other applications without having to code all the REST code yourself. There is currently no documentation on using the modules from Python, please inspect the source code.

The following modules are available:


* ``igorVar`` allows issuing standard REST methods to the Igor server.
* ``igorControl`` builds on that to allow starting, stopping and introspection of your Igor server.
* ``igorSetup`` allows programmatic installation and cofiguration of your Igor server.
* ``igorCA`` allows programmatic creation of certificates.
* ``igorServlet`` allows easy creation of REST services that can be *used* by Igor, with all the handling of SSL and capability checking and such done automatically for you.

~/.igor directory structure
---------------------------

The ``~/.igor`` directory can contain the following files and subdirectories:


* ``database.xml`` The main XML database.
* ``database.xml.YYYYMMDDHHMMSS`` Backups of the database (created automatically).
* ``plugins`` directory with installed plugins. Many will be symlinks into ``std-plugins`` directory.
* ``std-plugins`` symlink to standard plugins directory in the igor package (will be re-created on every startup).
* ``igor.log`` the *httpd-style* log of all Igor activity.
* ``igor.log.*`` older logfiles.
* ``igor.crt`` and ``igor.key`` if Igor is run in *https* mode these are the certificate and key used. ``igor.crt`` is also used by *igorVar* and *igorControl* to check the server identity.
* ``ca`` certificate authority data such as signing keys and certificates.
* ``igorSessions.db`` may be available to store igor user sessions.
* ``igor.cfg`` configuration file for *igorVar*\ , *igorControl* and *igorCA* (not used by *igorServer* or *igorSetup*\ ). Default argument values are stored in the ``[igor]`` section, with names identical to the long option name. By supplying the ``--config`` argument to *igorVar* or one of the other tools another section can be selected.

So, the following ``igor.cfg`` file will change the default server used by *igorVar* and *igorControl*\ :

.. code-block:: ini

   [igor]
   url = https://myigor.local:9333/data

Default option values can also be specified in the environment by specifying the name in capitals and prefixed with IGORSERVER\_. So the following environment variable setting will have the same effect:

.. code-block:: sh

   IGORSERVER_URL="https://myigor.local:9333/data"
