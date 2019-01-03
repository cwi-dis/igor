Python modules
==============

Igor comes with a number of Python extension modules to access and control the database.
These modules actually also implement the functionality of the corresponding
Igor command line tools.
 
igorVar
-------

*igorVar* is the main module used to access the database from Python programs. 
It allows getting and setting of database variables in
various different formats (text, xml, json, python).


.. automodule:: igorVar
	:members: IgorError

.. autoclass:: igorVar.IgorServer
	:members: get, put, post, delete, _action

igorCA
------

*igorCA* is the Python interface to using Igor as a Certificate Authority.
It can run all needed ``openssl`` commands locally, but will usually be used to
communicate with another *igorCA* embedded in Igor through the REST interface.

.. automodule:: igorCA
	:members:
	:undoc-members:

igorServlet
-----------

This module allows you to easily create a REST microservice that supports
Igor capability-based access control. You create an *IgorServlet* object
passing all the parameters needed to listen for requests and check capabilities.

You supply callback methods for the REST endpoints and start the service. 

Then, as requests come in, capabilities are checked, the REST parameters are decoded and
passed as arguments to your callback methods, the return value of your
callback is optionally JSON-encoded and sent back to the caller.

Intended use is that the requests come from the Igor server, and the microservice
implements a device or sensor (or group of sensors), or is used to check the status
of a service.

.. automodule:: igorServlet
	:members:
	
argumentParser arguments
^^^^^^^^^^^^^^^^^^^^^^^^

If you use *igorServlet.IgorServlet.argumentParser()* to create your *argparse*
parser your program will have the following arguments (aside from any you add yourself):

.. argparse::
	:ref: igorServlet.argumentParser
	:prog: igorServlet
	:nodefaultconst:
	