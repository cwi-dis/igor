Implementation details
======================

.. _directory-structure:

~/.igor directory structure
---------------------------

The ``~/.igor`` directory can contain the following files and subdirectories:


* ``database.xml`` The main XML database. See :doc:`schema` and :doc:`capabilities` for the format.
* ``database.xml.YYYYMMDDHHMMSS`` Backups of the database (created automatically).
* ``shadow.xml`` Database for secrets. Structurally identical to main database but only contains issuer shared secret keys.
* ``plugins`` directory with installed plugins. Many will be symlinks into ``std-plugins`` directory.
* ``std-plugins`` symlink to standard plugins directory in the igor package (will be re-created on every startup).
* ``igor.log`` the *httpd-style* log of all Igor activity.
* ``igor.log.*`` older logfiles.
* ``igor.crt`` and ``igor.key`` if Igor is run in *https* mode these are the certificate and key used. ``igor.crt`` is also used by *igorVar* and *igorControl* to check the server identity.
* ``ca`` certificate authority data such as signing keys and certificates.
* ``igorSessions.db`` may be available to store igor user sessions.
* ``igor.cfg`` configuration file for *igorVar*\ , *igorControl* and *igorCA* (not used by *igorServer* or *igorSetup*\ ). See :ref:`configuration-file` for details.

Internal APIs
-------------

This section still needs to be written. For now you have to look at the source code.
Here is a quick breakdown of the object structure to get you started:

The toplevel singleton object is of class ``IgorServer``, declared in __main__.py. It is usually called ``igor`` in plugins and such, and many objects have a ``self.igor`` backlink to this object.

The igor object has the following attributes that are considered part of its public (internal) interface:

* ``pathnames`` is an object storing all relevant pathnames.
* ``internal`` (class ``__main__.IgorInternal``) implements the methods of the ``/internal`` REST endpoint.
* ``access`` (class ``access.__init__.Access``) implements capabilities, access control, external shared secret keys and storage of all these.
* ``database`` is the low-level XML database (class ``xmlDatabase.DBImpl``) which allows fairly unrestricted access to all data, including the underlying DOM tree.
* ``databaseAccessor`` is a higher level, more secure API to the database (class ``webApp.XmlDatabaseAccess``).
* ``urlCaller`` is used to make REST calls, both internally within Igor and to external services (class ``callUrl.UrlCaller``)
* ``plugins`` is the plugin manager (class ``pluginHandler.IgorPlugins``)
* ``simpleActionHandler`` implements simpleActions, when they are triggered and what they do (class ``simpleActions.ActionCollection``)

Access Control Implementation
-----------------------------

*(version of 12-Nov-2017)*

**Note** that this description is seriously outdated.

The Igor access control implementation falls apart into two distinct areas:


* *mechanism*\ , how Igor implements that it is possible to check that a certain operation can proceed on a certain object in the current circumstances, and
* *policy*\ , the actual checking.

This document is about the *mechanism*\ , the *policy* is the subject of Pauline's research.

Mechanism API
^^^^^^^^^^^^^

Three types of objects are involved in the access checking mechanism. The whole implementation is in the module ``igor.access``. This module will eventually contain the policy implementation as well (to replace the current strawman policy).

The naming of API elements (specifically the use of *token*\ ) reflects our current thinking about policy direction but is by no means limiting: a token could just as easily contain an *identity* and *token checking* would then be implemented as *ACL checking*.

But, of course, the API may change to accomodate the policy.

Object Structure
^^^^^^^^^^^^^^^^

The main object is a singleton object ``igor.access.singleton`` of class ``Access``. This object is used by all other modules to obtain tokes and token checkers. It is a singleton because the database is a singleton too.

Tokens are represented by instances of the ``AccessToken`` class (or classes with the same API). An ``AccessToken`` can represent an actual token (supplied by an incoming HTTP request or picked up by an Igor *action* for outgoing or internal requests), but there are also special implementations for *"No token supplied"* and *"Igor itself"*. The latter is used, for example, when Igor updates its *last boot time* variable, and has no external representation.

Tokens are checked by instances of the ``AccessChecker`` class. Whenever *any* operation on *any* object is attempted an access checker for that object is instantiated. It is passed the *token* accompanying the operation, and decides whether the operation is allowed.

Integration
^^^^^^^^^^^

Integration with the rest of Igor is very simple. All database access methods require a *token* parameter, and before returning any XML element (or the value from any XML element, or before modifying or deleting the XML element) they obtain an *AccessChecker* for the object. The operation only proceeds if the *AccessChecker* allows it.

..

   As of this writing access checking is not fully implemented for XPath functions yet, so it is theoretically possible to obtain data from an element by not accessing the element directly but by passing it through an XML function. This will be addressed later.


The higher level API calls also all have a *token* parameter, and usually simply pass the token on to the lower layers.

At the top level of incoming HTTP requests the token is obtained from the HTTP headers (or something similar).

At the top level of *action* firing the token is obtained from the action description in the database (possibly indirectly).

..

   There is a bit of *policy* here: it may turn out we want to carry the original token that caused the action to fire, or maybe a token representing the union of the two tokens.


Plugins are similar to actions, they can also carry their own token.

Access Interface
^^^^^^^^^^^^^^^^

The ``Access`` object has four methods:


* ``checkerForElement(element)`` returns an ``AccessChecker`` instance for the given XML element. The intention is that this checker can be cached (for example as a hidden pointer on the XML element implementation) as long as it is deleted when the access policies for the element change.
* ``tokenForRequest(headers)`` returns an ``AccessToken`` for an incoming HTTP request.
* ``tokenForIgor()`` returns a special token for internal Igor operations.
* ``tokenForPlugin(name)`` returns a token for the plugin with the given name. *(this API is expected to change)*
* ``tokenForAction(element)`` returns the token for the action whose XML element is passed in.

AccessToken interface
^^^^^^^^^^^^^^^^^^^^^

The ``AccessToken`` object has one method:


* ``addToHeaders(headers)`` called when a token should be carried on an outgoing HTTP request. If the token has a valid externl representation it adds that representation to the ``headers`` dictionary.  *(this API is expected to change)*

AccessChecker interface
^^^^^^^^^^^^^^^^^^^^^^^

The ``AccessChecker`` object has one method:


* ``allowed(operation, token)`` return ``True`` if ``token`` (which is an ``AccessToken``\ ) has the right to execute ``operation``. Currently ``operation`` is a string with the following possible values:

  * ``'get'`` (read the element)
  * ``'put'`` (modify the element)
  * ``'post'`` (to create children elements)
  * ``'delete'`` (remove the element)
  * ``'run'`` (run the action or plugin)
