Initial setup
=============

Make sure you have first installed the Igor software, according to the instructions in :doc:`install`.

Setup the database
------------------

Create an initial empty database with

.. code-block:: sh

   igorSetup initialize

The default database is stored in ``~/.igor``.  Currently, Igor databases are *not* compatible between versions, so if you have used an older version of Igor you should first remove the old database.

Next add the standard plugins:

.. code-block:: sh

   igorSetup addstd systemHealth ca user device actions editData
   igorSetup addstd lan home say

The first set of those are plugins that are used for Igor administration. Technically
they are optional, i.e. Igor itself will work fine without them, but practically they are
needed to allow you to administer your Igor server.

The second set are really optional, but they provide convenience functions such as checking
that the internet works, and determining how any people ar currently at home. You may
want to skip installing these right now and add them later via the :doc:`administration`
interface.

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


Setup security
--------------

It is advisable to run Igor with the secure *https* protocol as opposed to the completely open *http* protocol. 
Igor can use any SSL certificate, but simplest is to configure Igor as a Certificate Authority.

Setup Igor as a CA
^^^^^^^^^^^^^^^^^^

Enabling Igor as a Certificate Authority (CA) for the ``.local`` domain is the generally the best option (but see below for alternatives). Details on using Igor as a CA are in :doc:`programs` but here is the information to get started.

A CA needs a well-known name, so that people who receive a certificate signed by it can see who they ultimately trust by trusting that certificate.
Even though it is rather pointless for our ``.local`` CA you will still have to specify the mandatory fields *country*, *state*, *organization* and it is a good idea to specify *common name*.
You also need a different *common name* for the intermediate issuer. Initialize your CA with the following command, but replace *igor.local*, *NL*, *Netherlands* and *Jack Jansen* with values that make sense for your situation:

.. code-block:: sh

   igorCA initialize '/CN=root.ca.igor.local/C=NL/ST=Netherlands/O=Jack Jansen' '/CN=intermediate.ca.igor.local/C=NL/ST=Netherlands/O=Jack Jansen'

(After this you don't really need the CA root key on your machine anymore, because the CA intermediate key will be used for everything. The directory ``~/.igor/ca/root`` has been made inaccessible, but if you are really security-conscious you can put its content on a USB stick, put it in a safe and remove all of ``~/.igor/ca/root``).

Now you can use your newly-created CA to sign the certificate for the Igor server:

.. code-block:: sh

   igorCA self igor.local localhost 127.0.0.1 ::1

The ``self`` command should be given all hostnames and IP addresses via which you expect to access Igor, and the "canonical name" should be first. So, the ``igor.local`` in the example above should be replaced by the DNS or mDNS name you normally use to access this host.

If you ever want to access Igor from Windows you should be aware of the fact that Windows does not have good support for mDNS `.local` names. You must either install some extension that supports this, or you must ensure that your Igor host has a fixed IP address and also add that address to the list of hostnames and IP addresses.

Finally you need to install the root certificate for the Igor CA into Igor and (if you want to access Igor with a browser or other software) into your system set of trusted root certificates. How this is done depends on whether you run Linux or OSX and which version you run (google for *"install root certificate"* with your OS name) but you get the Igor CA root certificate chain with the following command:

.. code-block:: sh

	igorCA getRoot
	
More commands are forthcoming here.
		
Alternative: Use another Igor as CA
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you already have another instance of Igor running on the local network and that other Igor has been setup as a CA you can set things up
so that this Igor uses the CA of the other Igor.

Let's say the other igor is running on machine *masterigor.local*. You can create a secret key and a Certificate Signing Request, and then ask the
other Igor to sign the certificate with the following command:

.. code-block:: sh

	igorCA --remote --url https://masterigor.local:9333/data/ --noverify self igor.local localhost 127.0.0.1 ::1
	
And again, you have to get and install the root certificate:

.. code-block:: sh

	igorCA --remote --url https://masterigor.local:9333/data/ --noverify getRoot
	
Alternative: Self-signed Certificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. deprecated:: 0.9
	Enabling Igor as a CA is better than using a self-signed certificate, because with a self-signed certificate you will have
	to go through a lot of ominous-sounding security dialogs for each browser with which you want to access Igor.
	
To use a self-signed certificate for Igor, run

.. code-block:: sh

   igorSetup certificate

And restart Igor. Igor will detect that it has a certificate and start up in secure mode.

Now connect your browser to https://localhost:9333. You will get a number of warnings about an untrusted website (because you used a self-signed certificate), read these and select all the answers that indicate you trust this website. This needs to be done only once per browser per user per machine.

Alternative: Use a real certificate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you happen to have access to a real trusted CA and your Igor runs on a machine with a public DNS domain name you can use the following command
(after supplying the correct hostname) to create a secret key and Certificate Signing Request:

.. code-block:: sh

   igorCA selfCSR igor.your.domain.name
   
This will store the secret key in the file `~/.igor/igor.key` and output the CSR (certificate signing request). You send this CSR to your CA,
which will sign it and return you a certificate. You store this certificate in `~/.igor/igor.crt` (in PEM format).

Alternative: run without https
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is possible to run Igor without *https*, using only *http* access, but this is only advisable in very specific situations where you know
you network is physically secure and completely isolated from the internet. You simply don't run any *igorCA* commands, and Igor will start up
using the http protocol (after issuing a warning). If you had previously already created certificates and keys and such and you want to revert
to http mode you can remove ``~/.igor/ca``, ``~/.igor/igor.key`` and ``~/.igor/igor.crt``.

Capability-based access control
-------------------------------

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

You will need to configure your Igor to do something useful. On the Igor landing page there are links to pages that allow you to add *devices*\ , *plugins* and *users*. 

	Note: this functionality is currently incomplete, so some things will have to be configured manually.  Specifically: actions cannot be created through a user interface.

Manual configuration
^^^^^^^^^^^^^^^^^^^^

The database is an XML file, so it can be edited in a normal text editor. But: you should make sure Igor is not running while you are editing, or it may override your changes.

See :doc:`schema` and :ref:`directory-structure` for information
on how to add things manually.


The following command helps you with stopping Igor during an edit and restarting it afterwards:

.. code-block:: sh

   igorSetup edit

Starting automatically
----------------------

Igor can be started automatically at system boot with the following command:

.. code-block:: sh

   igorSetup runatboot
   
On OSX and Linux this should start Igor as a deamon process. Igor will run under your user ID, and use the `.igor` database in your
home directory.
