Implementation details
======================

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
