Installation
============

Prerequisites
-------------

You need to have Python 3.6 or later installed.
(Python 2.7 is also still supported but Python 3 is preferred).

You need *pip* and *setuptools* (if not already included in your Python installation). Installing Python's package installation program *pip* will also install *setuptools*.

Your system might well have both Python 2.7 and Python 3.X installed, for that reason it is best to always use the commands ``python3`` and ``pip3`` (as opposed to ``python`` and ``pip``\ , which could refer to 2 or 3 depending on circumstances).

See also https://packaging.python.org/tutorials/installing-packages/.

Installing from PyPi
--------------------

At the moment Igor isn't hosted on PyPi. Once it is this section will be written.

Installing from source
----------------------

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

Testing the software (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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

	*Note:* currently the database format (particularly the schema) may change between releases.
	You should check the release notes to ensure your database is still compatible, and otherwise
	convert it manually after updating.
	
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
