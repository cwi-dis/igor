Command line utilities
**********************

Igor comes with a number of command line utilities to access and control the database.
Most of these use a common configuration file ``~/.igor/igor.cfg``
and a number of environment variables to set defaults for arguments.
 
igorVar
-------
.. index::
	single: igorVar (command line utility)


*igorVar* is the main program used to access the database from the command line
and from shell scripts. It allows getting and setting of database variables in
various different formats (text, xml, json, python).

.. argparse::
	:ref: igorVar.argumentParser
	:prog: igorVar
	:nodefaultconst:
	
	
	var : @replace
		Variable to get (or put, or post). The variable is specified in XPath
		syntax. Relative names are relative to the toplevel ``/data`` element in the
		database. Absolute names are also allowed (so ``/data/environment`` is equivalent
		to ``environment``).
		
		Access to non-database portions of the REST API is allowed, so
		getting ``/action/save`` will have the side-effect of saving the database.
		
		Full XPath syntax is allowed, so something like ``simpleActions/action[name='save']``
		will retrieve the definition of the *save* action. For some XPath expressions,
		such as expressions with a toplevel XPath function, it may be necessary to
		pass the ``--eval`` switch.
		
Some examples may help understanding how *igorVar* can be used to access and modify your
database. The following command will create a variable (in the ``sandbox`` section of the
database, which is specifically there for experimenting), assuming it does not exist yet.
It will print the full XPath of the variable created.

.. code-block:: sh

	igorVar --put text/plain --data "Hello world" sandbox/helloworld
	
Running that command multiple times will overwrite the variable. Running the following
command is completely equivalent:

.. code-block:: sh

	echo "Hello World" | igorVar --put text/plain sandbox/helloworld

You can get the plaintext value of variable with either of the following commands (which are completely equivalent):

.. code-block:: sh

	igorVar --mimetype text/plain sandbox/helloworld
	igorVar --mimetype text/plain /data/sandbox/helloworld
		
The default mimetype, however, is ``application/xml`` because *igorVar* is primarily meant
for use in scripts, not interactively by a human.

To delete a variable, if it exists, use

.. code-block:: sh

	igorVar --delete sandbox/helloworld
	
Post is similar to put, but always create a new entry. So if you have no
*helloworld* variable yet the following command line is equivalent to the first
example. But if you run it three times you will have three variables, named
``sandbox/helloworld[1]``, ``sandbox/helloworld[2]`` and ``sandbox/helloworld[3]``:

.. code-block:: sh

	igorVar --post text/plain --data "Hello world one" sandbox/helloworld
	igorVar --post text/plain --data "Hello world two" sandbox/helloworld
	igorVar --post text/plain --data "Hello world three" sandbox/helloworld
	
To retrieve one of these you *must* supply the index. Or use ``--variant multi`` but
that only works when you want the value in JSON or XML:

.. code-block:: sh

	igorVar --mimetype text/plain 'sandbox/helloworld[2]'
	igorVar --mimetype application/json --variant multi sandbox/helloworld
	
Note that this ``[2]`` construct is an XPath expression. Read up on XPath, it is a very
powerful but simple language to select variables in your database. Also note that many XPath
operators are also magical to the shell, so put your variable name in single or double
quotes when in doubt. 

igorCA
------
.. index::
	single: igorCA (command line utility)


*igorCA* is the command line interface to using Igor as a Certificate Authority.
Under the hood it is implemented using the ``openssl`` command line tool. It is
intended to serve as CA for the ``.local`` domain, to enable secure communication
between local devices and Igor (and other local devices).

When used as a command line tool *igorCA* can also comunicate to another
*igorCA* operating as a plugin in another Igor, thereby making it possible to
run the CA only on a single machine in the local network, even if multiple
Igor instances are used. This mode of operation is enabled by using the *--remote* argument
to *igorCA*.

.. argparse::
	:ref: igorCA.argumentParser
	:prog: igorCA
	:nodefaultconst:

igorCA actions
^^^^^^^^^^^^^^

``initialize``	*root-issuer* *intermediate-issuer*
	Create CA infrastructure, root key and certificate and intermediate key and certificate. 
	
	The *root-issuer* argument is the name of this Certificate Authority, according to the X.509 standard. 
	See <https://tools.ietf.org/rfc/rfc5280.txt> section 4.1.2.4 for exact details of the fields allowed, but some
	fields are required: *C* for country name, *ST* for state and *O* for organization. Adding *CN* for common name is probably a good idea, this will allow people on the local network to recognize the certificate issuer.
	
	The fields are introduced by slashes, so the following is an example of what you could use as *root-issuer* after replacing the various fields with the correct values for your situation:
	
	``'/CN=root.ca.igor.local/C=NL/ST=Netherlands/O=Jack Jansen'``
	
	
	The *intermediate-issuer* is the same, but for the intermediate certificate. ``CN=intermediate.ca.igor.local`` is suggested.
	
``getRoot``   	
	Returns the signing certificate chain (for installation in browser or operating system).
``status``    	
	Returns nothing if CA status is ok, otherwise error message
``csrtemplate``	
	Return template config file for openSSL CSR (Certificate Signing Request)
``dn``        	
	Return CA distinghuished name as a JSON structure
``gen`` *prefix* *name-or-ip* [...] 	
	Generate a a server key and certificate for a named service and sign it with the intermediate Igor CA key.
	The *prefix* is used to generate the filenames where the results of this action are stored:
	
	* *prefix*\ ``.key`` will contain the secret key for the service
	* *prefix*\ ``.crt`` will contain the certificate for the service
	* *prefix*\ ``.csr`` is a temporary file containing the CSR
	* *prefix*\ ``.csrConfig`` is a temporary containing the openSSL configuration used to create the CSR
``sign`` *csrfile* *certfile*
	Read a Certificate Signing Request from *csrfile* and sign it with the CA keys. Save the resulting certificate to ``certfile``.
``selfCSR`` *name-or-ip* [...]
	Create secret key and CSR (Certificate Signing Request) for Igor itself. Pass all DNS names (or IP addresses) for this Igor host as arguments. Outputs CSR.
``self`` *name-or-ip* [...]
	Create a secret key and certificate for Igor itself, and sign it with the intermediate Igor CA key.
``revoke`` *number*
	Revoke a certificate. Argument is the number of the certificate to revoke (can be obtained through the *list* action or by inspecting the certificate). Regenerates CRL as well.
``genCRL``    	
	Generate CRL (Certificate Revokation List) in ``static/crl.pem`` so it can be retrieved by other Igors.
``getCRL``    	
	Output the CRL (Certificate Revocation List), for example for use in browsers or in the operating system certificate support.
``list``      	
	Return list of certificates signed and certificates signed and subsequently revoked.
	
igorControl
-----------
.. index::
	single: igorControl (command line utility)


*igorControl* allows some control over a running Igor, through the REST interface. All functions it allows can
also be accessed through *igorVar* but *igorControl* provides a more convenient interface.

.. argparse::
	:ref: igorControl.argumentParser
	:prog: igorControl
	:nodefaultconst:

igorControl actions
^^^^^^^^^^^^^^^^^^^
version
	Show Igor version.
save
	Saves the database to the filesystem.
stop
	Gracefully stop Igor.
restart
	Attempt to gracefully stop and restart Igor.
log
	Show current igor log file.
dump
	Show internal run queues, action handlers and events.
fail
	Raises a Python exception (intended for testing only).
flush
	Wait until all currently queued urlCaller events have been completed (intended for testing only).

igorSetup
---------
.. index::
	single: igorSetup (command line utility)


*igorSetup* is the utility to initialize an Igor installation on the current machine and
control it from the command line. Unlike the other command line utilities this utility
uses normal Unix/Linux filesystem access and process control, and it can therefore only be used on
the machine that also runs Igor (and by a user that has the right Unix permissions).

.. argparse::
	:ref: igorSetup.argumentParser
	:prog: igorSetup
	:nodefaultconst:

igorSetup actions
^^^^^^^^^^^^^^^^^
``initialize``
	create empty igor database.
``runatboot``
	make igorServer run at system boot (Linux or OSX, requires sudo permission).
``runatlogin``
	make igorServer run at user login (OSX only).
``start``
	start service (using normal OSX or Linux commands).
``stop``
	stop service (using normal OSX or Linux commands).
``add`` *pathname* [...]
	add plugin (copy) from given *pathname*. Only use this command while Igor is not running. Note that it is potentially
	dangerous to install an Igor plugin, especially if it comes from an unknown source: an Igor plugin currently has
	complete access to the Igor internals, and can therefore access any data or modify it, and probably also read or
	write files on your Igor host.
``addstd`` *name*[=*srcname*] [...]
	add standard plugin *srcname* (linked) with given *name*. Only use this command while Igor is not running. Using the `plugin.html` Igor interface is easier.
``remove`` *name* [...]
	remove plugin *name*.  Using the `plugin.html` Igor interface is easier.
``list``
	show all installed plugins.  Using the `plugin.html` Igor interface is easier.
``liststd``
	list all available standard plugins.  Using the `plugin.html` Igor interface is easier.
``certificate`` *hostname* [...]
	create https certificate for Igor using Igor as CA (using the igorCA module). Only use this command while Igor is not running. 
``certificateSelfSigned`` *subject* *hostname* [...]
	create self-signed https certificate for Igor (deprecated, use ``certificate`` command in stead). Only use this command while Igor is not running. 
``edit``
	stop, edit the database (using the ``$EDITOR`` program) and restart the service.
``rebuild``
	stop, rebuild and restart the service (must be run in source directory).
``rebuildedit``
	stop, edit database, rebuild and start the service (must be run in source directory).

.. _configuration-file:

Configuration file
------------------

.. index::
	single: igor.cfg configuration file



*igorVar*, *igorCA* and *igorControl* all read default values for named arguments from a configuration
file ``~/.igor/igor.cfg``, section ``[igor]`` (but these are overridable through the ``--configFile`` and ``--config`` arguments).

The following *igor.cfg* file causes ``igorVar`` to access an Igor on machine *downstairs.local* and ``igorVar --config upstairs`` to
access an Igor an machine *upstairs.local* with HTTPS certification turned off::

	[igor]
	url = https://downstairs.local:9333/data/
	[upstairs]
	url = https://upstairs.local:9333/data/
	noverify = 1


Environment variables
---------------------
.. index::
	single: IGORSERVER_* environment variables



*igorVar*, *igorCA* and *igorControl* can also get their default values for named arguments from environment variables. These environment
variables start with ``IGORSERVER_`` followed by the upper-cased argument name. As an example, ``IGORSERVER_URL`` can be used to provide
a default for the ``--url`` argument.

Values passed on the command line have the highest priority, then values in environment variables, then values read from the configuration
file.
