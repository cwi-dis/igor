# Using Igor

## Prerequisites

You need to have Python 3.6 or later installed.
(Python 2.7 is also still supported but Python 3 is preferred).

You need _pip_ and _setuptools_ (if not already included in your Python installation). Installing Python's package installation program _pip_ will also install _setuptools_.

Your system might well have both Python 2.7 and Python 3.X installed, for that reason it is best to always use the commands `python3` and `pip3` (as opposed to `python` and `pip`, which could refer to 2 or 3 depending on circumstances).

See also <https://packaging.python.org/tutorials/installing-packages/>.

## Installing the software

Download the source via <https://github.com/cwi-dis/igor>. 
```
git clone https://github.com/cwi-dis/igor
```

Then change into the `igor` directory, and install with

```
sudo pip3 install -r requirements.txt
python3 setup.py build
sudo python3 setup.py install
```

This will install the main binary `igorServer` as well as the utilties `igorVar`, `igorSetup`, `igorControl` and `igorCA`.

The instructions above, using `sudo` for installation, will install Igor and the required dependencies for all users on your system. Installing for the current user only may be possible but is untested.

You may also want to install some of the helper utilities from the `helpers` subdirectory.

## Setup the database

You create an initial empty database with

```
igorSetup initialize
```
The default database is stored in `~/.igor`.  For now, Igor databases are _not_ compatible between versions, so if you have used an older version of Igor you have to first remove your old database.

Next add the standard plugins you need with

```
igorSetup addstd lan systemHealth ca user device
```

(these are the standard plugins used by the default database, which as distributed does little more than checking the health of your internet connection).

At this point you should be able to run the server with

```
igorServer
```

and point your browser at <http://localhost:9333> to see Igor in action.

At any time the server is not running you can check the consistency of the database, with

```
igorServer --check
```

or alternatively you can try to automatically fix it with

```
igorServer --fix
```

## Testing the software

There is a unittest-based test suite in the `test` subdirectory. The easiest way to run the tests is to first install the software (as per the instructions above) and then run

```
python3 setup.py test
```

This will run all tests in various configurations (with and without https support, with and without capability support, etc). This will run the tests in complete isolation, using a separate temporary install and separate Igor instances running on different ports, etc. So it will not interfere with your installed igor.

If you want more control (for example to specify test options and such) you can in stead use the following command line (which will use the Igor version installed on your system): 

```
python3 -m test.test_igor
```

It is also possible to test the performance of Igor (again with the various configurations):

```
python3 -m test.perf_igor
```

will run a set of actions similar to the unittests (for a minimum number of calls and a minimum duration) and report number of calls, average runtime per call and standard deviation of the runtimes.

### Security

It is advised to run Igor with the secure _https_ protocol as opposed to the completely open _http_ protocol. Igor can use any SSL certificate, but simplest is to use a self-signed certificate or to configure Igor as a Certificate Authority.

#### Igor as a CA

Enabling Igor as a Certificate Authority is the best option if there are other services (such as [Iotsa](https://github.com/cwi-dis/iotsa)-based devices, or other Igors) that you want to protect with _https_. Details on using Igor as a CA are in [../igor/plugins/ca/readmd.md](../igor/plugins/ca/readme.md) but here are the commands needed to get this kickstarted:

```
igorCA initialize
igorCA self igor.local localhost 127.0.0.1 ::1
```

The `self` command should be given all hostnames and IP addresses via which you expect to access Igor, and the "canonical name" should be first.

#### Self-signed Certificate

Alternatively, to use a self-signed certificate for Igor, run

```
igorSetup certificate
```

And restart Igor. Igor will detect that it has a certificate and start up in secure mode.

Now connect your browser to <https://localhost:9333>. You will get a number of warnings about an untrusted website (because you used a self-signed certificate), read these and select all the answers that indicate you trust this website. This needs to be done only once (per browser).

#### Capability-based access control

Igor has support for experimental fine grained access control, using capabilities. On top of that there is user-based (login) access control.

This feature is incomplete, especially the documentation is lacking, therefore it is not enabled by default. If you want to experiment you can use first

```
igorServer --capabilities --fix
```

to add the required set of minimal capabilities to your database, and then run

```
igorServer --capabilities
```

to run your server in capability-based acess control mode. You will probably need various visits to the _/users.html_, _/devices.html_ and _/capabilities.html_ administrative interfaces to get anything to work.

It is also possible to let Igor go through all the motions of capability-based access control, but allowing the operations even if the capabilities would disallow it. This can be handy while converting your database to use capabilities: you will get all the error messages about missing capabilities, but as warnings only. Therefore your Igor server will function as if no capabilities were in use. Enable this mode with

```
igorServer --warnCapabilities
```

### Igor configuration

You will need to configure your Igor to do something useful. On the Igor landing page there are links to pages that allow you to add _devices_, _plugins_ and _users_. However, this functionality is currently incomplete, so various things will have to be configured manually.

#### Manual configuration

See [../igor/std-plugins/readmd.md](../igor/std-plugins/readme.md) for a list of useful plugins that are included with Igor, and [schema.md](schema.md) for how to add useful actions to your database.

Stop Igor before editing your `~/.igor/database.xml` in a text editor. The following command helps you with this:

```
igorSetup edit
```

### starting automatically

Igor can be started automatically at system boot with the following command:

```
igorSetup runatboot
```
## Command line utilities

### igorSetup

Utility to help with configuring Igor. This utility has to be run on the same computer as _igorServer_ runs on. Various subcommands were explained in the previous section, calling `igorSetup` without arguments will give concise help on the available subcommands.

### igorControl

Runtime control over Igor: stopping the service, saving the database, etc.

Uses the _http[s]_ interface so can be run on a different computer. Configuration parameters can be obtained from `~/.igor/igor.cfg` or environment variables, see below.

`igorControl help` should list the available commands.

### igorVar

Accesses the database to read or write variables.

Uses the _http[s]_ interface so can be run on a different computer. Configuration parameters can be obtained from `~/.igor/igor.cfg` or environment variables, see below.

`igorVar --help` explains the parameters.

The _igorVar_ utility can also be used to communicate with other services that have a REST-like interface and uses JSON or XML as data format.

### igorCA

Certificate Authority command line tool. Call `igorCA help` for a list of commands. More detail (a little more:-) can be found in [../igor/plugins/ca/readmd.md](../igor/plugins/ca/readme.md).

## Supporting modules

The command line tools listed above also do double duty as importable Python modules, enabling accessing Igor from other applications without having to code all the REST code yourself.

The following modules are available:

- `igorVar` allows issuing standard REST methods to the Igor server.
- `igorControl` builds on that to allow starting, stopping and introspection of your Igor server.
- `igorSetup` allows programmatic installation and cofiguration of your Igor server.
- `igorCA` allows programmatic creation of certificates.
- `igorServlet` allows easy creation of REST services that can be _used_ by Igor, with all the handling of SSL and capability checking and such done automatically for you.

## ~/.igor directory structure

The `~/.igor` directory can contain the following files and subdirectories:

- `database.xml` The main XML database.
- `database.xml.YYYYMMDDHHMMSS` Backups of the database (created automatically).
- `plugins` directory with installed plugins. Many will be symlinks into `std-plugins` directory.
- `std-plugins` symlink to standard plugins directory in the igor package (will be re-created on every startup).
- `igor.log` if _igorServer_ is started at system boot this is the _httpd-style_ log of all Igor activity.
- `igor.log.*` Older logfiles.
- `igor.crt` and `igor.key` if Igor is run in _https_ mode these are the certificate and key used. `igor.crt` is also used by _igorVar_ and _igorControl_ to check the server identity.
- `ca` certificate authority data such as signing keys and certificates.
- `igorSessions.db` may be available to store igor user sessions.
- `igor.cfg` configuration file for _igorVar_ and _igorControl_ (not used by _igorServer_ or _igorSetup_). All values are stored in the `[igor]` section, with names identical to the long option name. So, the following file will change the default server used by _igorVar_ and _igorControl_:

	```
	[igor]
	url = https://myigor.local:9333/data
	```
	
	Default option values can also be specified in the environment by specifying the name in capitals and prefixed with IGORSERVER_. So the following environment valiable setting will have the same effect:
	
	```
	IGORSERVER_URL="https://myigor.local:9333/data"
	```
