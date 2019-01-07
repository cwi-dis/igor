# home - some actions that make sense in a home setting

This plugin is mainly there to show *"it can be done"*. It is a plugin with only a database fragment, without
any Python or shell script implementation.

It contains a couple of actions that make sense in a home setting.

## actions

- *checkNight* updates the variable ``environment/night`` to reflect whether it is day or night. As included night starts at 23:00 and ends at 08:00.
- *updatePeople* updates the ``people/_name_/home`` boolean whenever a device owned by person ``_name_`` shows up or disappears  in ``environment/devices``.
- *countPeopleAtHome* updates ``environment/people/count`` to reflect how many people are currently considered to be at home.