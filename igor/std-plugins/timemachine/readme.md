# timemachine - Time Machine backup status

This plugin check when the most recent backup has been made with Apple Time Machine. It uses the `tmutil` utility, so the igor user must have the right access privileges to run that.

The following parameters are accepted:

* `name`: name of the service (string). This is used as the name of the element in `services`. Default `backup`.
* `remoteHost`: hostname or ip-address where `tmutil` is run, using `ssh`. Default is to run locally.

The status of the backup (including any error messages) is stored in `/data/status/services/_name_`.

## User Interface

There is a user interface page _index.html_ that allows adding of Time Machine service watchers and deleting them again.