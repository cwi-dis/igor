Setup Igor for the first time
=============================

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
