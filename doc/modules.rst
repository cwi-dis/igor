Modules
**********************

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
