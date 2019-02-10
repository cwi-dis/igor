# Access Control schema

Currently data pertaining to access control is stored in the main database, with an XML namespace of `http://jackjansen.nl/igor/authentication` (usually encoded with the `xmlns:au` prefix).

This data is hidden from normal Igor access (unless query parameter `.VARIANT=raw` is used). In principle this should be safe,
because an external call cannot modify the capabilities and there is no secret information contained in the capability data.
There is however an issue that a call with the right permissions can accidentally delete a capability be replacing a subtree (with `PUT`).

## Capability structure

A capability is stored in an `au:capability` element.

* `comment` textual description, to keep us sane during development.
* `cid` unique ID of this capability.
* `child` one entry for each child (delegated) capability of this capability.
* `parent` parent of this capability.
* `delegate` boolean, if `true` this capability can be delegated. If the value is the string `external` this capability can be the parent of any capability as long as that new capability has an `aud` field.
* `obj` an XPath referencing a single element (or a nonexisting element with a single existing parent element) to which this capability refers. Rights on that object and its descendants are governed by a number of other fields:
	* `get` Together with `obj` defines on which elements this capability grants `GET` rights:
		* empty (or non-existent): none.
		* `self` the element itself only.
		* `descendant-or-self` the whole subtree rooted at the element (the element itself, its children, its grandchildren, etc).
		* `descendant` the whole subtree rooted at the element except the element itself.
		* `child` direct children of the element.
		* More values may be added later.
	* `put` Together with `obj` defines on which elements this capability grants `PUT` rights. Values as for `get`.
	* `post` Together with `obj` defines on which elements this capability grants `POST` rights. Values as for `get`.
	* `delete` Together with `obj` defines on which elements this capability grants `DELETE` rights. Values as for `get`.

The `obj` field will usually be an absolute XPath (starting with `/data`) but there are a number of other values used for non-database accesses (REST and other):

* `/action` is the virtual object tree of actions (the REST `/action` entrypoints)
* `/internal` is the virtual object tree of internal actions (the REST `/internal` entrypoints)
* `/plugin` is the virtual object tree of plugins (the REST `/plugin` entrypoint)
* `/filesystem` is the right to do operations that modify the filesystem. Checking this capability is currently only implemented for installing plugins.

Capabilities that have an external representation may have a few extra fields:

* `iss` Issuer of this capability. Usually the URL of `/issuer` on this igor.
* `aud` Audience of this capability. Required for capabilities that Igor will encode as a JWT (Json Web Token, <https://en.wikipedia.org/wiki/JSON_Web_Token>) in an outgoing `Authentication: Bearer` header.
* `sub` Subject of this capability. Required for capabilities that Igor receives as JWT in an incoming `Authentication: Bearer` header.
* For outgoing capabilities there may be other fields that are meaningful to the _audience_ of the capability.

External capabilities are protected using a symmetric key that is shared between Issuer and Audience (for outgoing capabilities) or Issuer and Subject (for incoming keys). This key is used to sign the JWT.

## Database schema additions

### /internal/accessControl

Not really part of the database, but this is the entry point to manage (list, delegate, revoke) capabilities.

### /data/au:access

Required for further schema requirements.

### /data/au:access/au:defaultCapabilities

Capabilities that will be used for any action, user or request that has no `Authentication: Bearer` header. For users and actions this set of capabilities is also valid if they have their own set. In other words: their own set augments the set of capabilities, it does not replace it.

These capabilities should be here:

- get(descendant-or-self), /data/environment
- get(descendant-or-self), /data/status
- get(descendant-or-self), /data/services/igor
- get(child), /static
- get(child), /internal/accessControl
- get(descendant-or-self)/put(descendant)/post(descendant)/delete(descendant), /data/sandbox

### /data/au:access/au:exportedCapabilities

Stores each `au:capability` for which an external representation has been created. Mainly so that each capability has an "owner".

### /data/au:access/au:revokedCapabilities

Stores all external capabilities that have been revoced. For each such capability there is a `au:revokedCapability` with at least a field `cid` that holds the capability ID. Optionally there is an `nva` field, Not Valid After, copied from the original capability, that indicates when this revoked capability can be cleaned up because the original is no longer valid.

### /data/au:access/au:unusedCapabilities

This is an optional area to store capabilities that  are valid but currently not used, and that have no owner. For Igor development, really.

### /data/au:access/au:sharedKeys

Empty placeholder for the secret shared key data in the _shadow.xml_ database (see below).

### /data/identities

Capabilities carried by all users that are logged in. Contains at least:

- get(descendent-or-self), /data/people

### /data/identities/admin

User that holds the master capabilities, capabilities with fairly unlimited access from which more limited capabilities are descended (through delegation).

There are at least the following capabilities, of which most other capabilities are descended (through delegation and narrowing the scope):

- get(descendant-or-self)+put(descendant)+post(descendant)+delete(descendant), /data
- get(descendant), /action
- get(descendant), /plugin
- get(descendant), /pluginscript
- get(descendant), /internal
- an empty capability (no rights, no object) with `cid=root` and no parent. This is the root of the capability tree.

### /data/identities/_user_

Capabilities this user will carry when logged in. Contains at least:

- get(descendent-or-self)+put(descendent)+post(descendent)+delete(descendent), /data/identities/_user_
- put(descendent)+post(descendent)+delete(descendent), /data/people/_user_

### /data/actions

Capabilities that are carried by all actions. Contains at least:

- get(descendant), /plugin
- get(child), /action

### /data/actions/action

Capabilities this action will carry when executing.

### /data/plugindata/_pluginname_/au:capability

Capabilities this plugin will carry when executing. Also available to the template pages and scripts for this plugin.

## Shadow database

The main igor database `.igor/database.xml` does not contain any secret information, so that access control secrets cannot be leaked accidentally through the REST interface.
Therefore, all secret information is kept in a separate database `.igor/shadow.xml` which has in principle the same structure as the main database, but only contains secret information.

In practice, the shadow database contains only the shared secret keys:

### /data/au:access/au:sharedKeys

Stores symmetric keys shared between Igor and a single external party. These keys are used to sign outgoing capabilities (and check incoming capabilities). Each key is stored in an `au:sharedKey` element with the following fields:

* `iss` Issuer.
* `aud` (optional) Audience.
* `sub` (optional) Subject.
* `externalKey` Symmteric key to use.

Keys are looked up either by the combination of _iss_ and _aud_ (for outgoing keys) or _iss_ and _sub_ (for incoming keys).

## Implementation details

This section lists some of the ideas that came up when designing the capability structure. They may not be true anymore, but the text is kept here because it is not currently stored anywhere else.

### Capability consistency checks

Capabilities need to be checked for consistency, and for adherence to the schema. 

The following checks are done as a first order check, and ensure the base infrastructure for the schema is in place:

- `/data/au:access` exists.
- `/data/au:access/au:defaultCapabilities` exists.
- `/data/au:access/au:exportedCapabilities` exists.
- `/data/au:access/au:revokedCapabilities` exists.
- `/data/au:access/au:unusedCapabilities` exists.
- `/data/au:access/au:sharedKeys` exists.
- `/data/identities` exists.
- `/data/identities/admin` exists.
- `/data/identities/admin/au:capability[cid='root']` exists.
- `/data/actions` exists.

As a second check we test that the default set of capabilities (as per the schema above) exist and are in their correct location.

As a third check we enumerate all capabilities and check the following assertions. These ensure that the tree of all capabilities is consistent:

-  Each capability must have a `cid`. 
-  This `cid` must be unique.
- Each capability (except `cid=root`) must have an existing `parent`, if not the capability is given `parent=root`.
- Each capability must have its `cid` listed in the parent `child` fields. If not it is added.
- Each `child` of each capability must exist. If not the `child` is removed.

As a fourth check we check that every capability is in an expected location. In other words, the DOM parent of the capability is one of:

- Any of the containers in the first check, or
- `/data/identities/*`
- `/data/plugindata/*`
- `/data/actions/action`

Capabilities that fail this check are moved into `/data/au:access/au:unusedCapabilities`.

### Actions on adding a new user

To be refined, but at least:

- Create `/data/people` entry.
- Create `/data/identities` entry,
	- Fill with capabilities mentioned above
	- Create password

The API will need at least _name_ and _password_. Because of access control policies it is implied that only the _admin_ user can call this API (or any agent that the _admin_ user has granted the corresponding capabilities to).

### Actions on deleting a user

- Move any non-standard capabilities (really: any capability with `aud` not the current Igor) to a safe place (probably the _admin_ user).
- Delete `/data/people` and `/data/identities` entries.

The API will need just the user name, and the same access control rules as for adding users will apply.

### Actions on adding a new device

- Create SSL key with `igorCA` (or `iotsa/extras/make-igor-signed-cert.sh` or via _/plugin/ca_) and copy the key and certificate to the device.
- Create a shared secret key with new device as audience, via _/capabilities.html_ or _/internal/accessControl_, and copy the secret key to the device.
- Create an initial "allow all API actions" capability for the device (TBD) and store it in some users' space (current user? admin user?)
	- Igor should automatically pick up the correct secret key and encode the capability with it, when talking to the device.
- If the device is also a _sensor_, i.e. if it can also trigger actions in Igor, all of the _sensor_ actions must also be done.

### Actions on adding a new sensor

- Create a shared secret key with the new sensor as subject, via _/capabilities.html_ or _/internal/accessControl_, and copy the secret key to the device.
- Create a capability (with the sensor as subject and audience Igor) for each action the sensor should be able to trigger.
- Export these capabilities (Igor will pick up the correct secret key based on the subject) and copy them to the sensor.

### Generalized API for adding a device or sensor

Data to be supplied to this action:

- Name of the device/sensor.
- Boolean _isSensor_.
- Boolean _isDevice_.
- Hostname or IP address of the sensor (defaults to name with _.local_ appended).
	- if _isDevice_ this will be used as the _audience_ of the first shared key.
	- If _isSensor_ this will be used as the _subject_ of the second shared key.
- if _isDevice_: Partial URL of the API of this device (such as _/api_). Will be the _object_ of the device access capability stored in the users' _identities_ entry.
- if _isSensor_: List of (_name_, _verb_, _object_) this sensor will contact (or empty for non-sensor devices). If non-empty the sensor shared key (audience Igor, subject the sensor) will be used to sign these.

Data returned:

- if _isDevice_:
	- SSL key
	- SSL certificate
	- shared device key
- if _isSensor_:
	- List of (_name_, _verb_, _url_, _signed capability_).

Data saved in Igor database:

- Shared keys (in the hidden area)
- if _isDevice_: Capability for accessing the device
- Entry in either `/data/devices` or `/data/sensors`.

It needs to be worked out what the access control rights are that are needed for this API. It seems as though no special rights are needed for devices, and for sensors the caller needs to have capabilities (with `delegate=true`) for each of the verb/object combinations.

It also needs to be worked out whether the user (or other agent) that calls this API gets permissions to the `/data/devices` or `/data/sensors` areas.

### Deleting a device or sensor

- The entries in `/data/devices` and `/data/sensors` should be deleted.
- The shared keys should be deleted.
- The SSL certificate should be revoked.

### Other actions on agent changes

To be determined what is needed when adding/removing/changing plugins and actions. 

Also to be determined whether anything needs to be done when certificates expire or are revoked.

Also to be determined what to do when secret keys are deleted and re-added.
