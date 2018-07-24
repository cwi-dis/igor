# Using Igor

## Prerequisites

You need to have Python v2.7 installed, and that should also have `setuptools` installed.

Installing Python's package installation program `pip` will also install `setuptools`.

See also https://packaging.python.org/tutorials/installing-packages/

## Installing the software

Download the source via <https://github.com/cwi-dis/igor>. Then install everything with

```
python setup.py build
sudo python setup.py install
```

This will install the main binary `igorServer` as well as the utilties `igorVar`, `igorSetup`, `igorControl` and `igorCA`.

You may also want to install some of the helper utilities from the `helpers` subdirectory.

## Setup the database

Your default database will be stored in `~/.igor`. You can create an initial empty database with

```
igorSetup initialize
```

Now you need to add the standard plugins you need with

```
igorSetup addstd lan systemHealth ca user device
```

(these are the standard plugins used by the default database, which by default does little more than checking the health of your internet connection. You can ignore the message about editing your database at this time).

At any time the server is not running you can check the consistency of the database, with

```
igorServer --check
```

or alternatively you can try to autmatically fix it with

```
igorServer --fix
```

At this point you should be able to run the server with

```
igorServer
```

and point your browser at <http://localhost:9333> to see Igor in action.

### Security

It is advised to run Igor with the secure _https_ protocol as opposed to the completely open _http_ protocol. Igor can use any SSL certificate, but simplest is to use a self-signed certificate or to configure Igor as a Certificate Authority.

#### Igor as a CA

Enabling Igor as a Certificate Authority is the best option if there are other services (such as Iotsa-based devices, or other Igors) that you want to protect with _https_. Details on using Igor as a CA are in [../igor/plugins/ca/readmd.md](../igor/plugins/ca/readme.md) but here are the commands needed to get this kickstarted:

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

### Igor configuration

You will need to configure your Igor to do something useful. See [../igor/plugins/readmd.md](../igor/plugins/readme.md) for a list of useful plugins, and [schema.md](schema.md) for how to add useful actions to your database.

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

## ~/.igor directory structure

The `~/.igor` directory can contain the following files and subdirectories:

- `database.xml` The main XML database.
- `database.xml.YYYYMMDDHHMMSS` Backups of the database (created automatically).
- `plugins` directory with installed plugins.
- `igor.log` if _igorServer_ is started at system boot this is the _httpd-style_ log of all Igor activity.
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
