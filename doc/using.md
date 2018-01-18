# Using Igor

## Installing the software

Download the source via <https://github.com/cwi-dis/igor>. The install everything with

```
python setup.py build
sudo python setup.py install
```

This will install the main binary `igorServer` as well as the utilties `igorVar`, `igorSetup` and `igorControl`.

You may also want to install some of the helper utilities from _helpers_.

## Setup the database

Your default database will be stored in `~/.igor`. You can create an initial empty database with

```
igorSetup initialize
```

Now you need to add the standard plugins you need with

```
igorSetup addstd lan systemHealth
```

(these are the two standard plugins used by the default database, which by default does little more than checking the health of your internet connection. You can ignore the message about editing your database at this time).

At this point you should be able to run the server with

```
igorServer
```

and point your browser at <http://localhost:9333> to see Igor in action.

### Security

It is advised to run Igor with the secure _https_ protocol as opposed to the completely open _http_ protocol. Igor can use any SSL certificate, but simplest is to use a self-signed certificate. Run

```
igorSetup certificate
```

And restart Igor. Igor will detect that it has a certificate and start up in secure mode.

Now connect your browser to <https://localhost:9333>. You will get a number of warnings about an untrusted website (because you used a self-signed certificate), read these and select all the answers that indicate you trust this website. This needs to be done only once (per browser).

### configuration

You will need to configure your Igor to do something useful. See [../igor/plugins/readmd.md](../igor/plugins/readmd) for a list of useful plugins, and [schema.md](schema.md) for how to add useful actions to your database.

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

## ~/.igor directory structure

The `~/.igor` directory can contain the following files and subdirectories:

- `database.xml` The main XML database.
- `database.xml.YYYYMMDDHHMMSS` Backups of the database (created automatically).
- `plugins` directory with installed plugins.
- `igor.log` if _igorServer_ is started at system boot this is the _httpd-style_ log of all Igor activity.
- `igor.crt` and `igor.key` if Igor is run in _https_ mode these are the certificate and key used. `igor.crt` is also used by _igorVar_ and _igorControl_ to check the server identity.
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