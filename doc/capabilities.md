# Access Control schema

For the time being, data pertaining to access control is stored in the main database, with an XML namespace of `http://jackjansen.nl/igor/authentication` (usually encoded with the `xmlns:au` prefix).

Eventually this data will be hidden from normal Igor access, or moved to a separate database.

## Capability structure

A capability is stored in an `au:capability` element.

* `comment` textual description, to keep us sane during development.
* `cid` unique ID of this capability.
* `child` one entry for each child (delegated) capability of this capability.
* `parent` parent of this capability.
* `delegate` boolean, if `true` this capability can be delegated.
* `obj` an xpath referencing a single element (or a nonexisting element with a single existing parent element) to which this capability refers. Rights on that object and its descendants are governed by a number of other fields:
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

Capabilities that have an external representation may have a few extra fields:

* `iss` Issuer of this capability. Usually the URL of `/issuer` on this igor.
* `aud` Audience of this capability. Required for capabilities that Igor will encode as a JWT in an outgoing `Authentication: Bearer` header.
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

### /data/au:access/au:exportedCapabilities

Stores each `au:capability` for which an external representation has been created. Mainly so that each capability has an "owner".

### /data/au:access/au:revokedCapabilities

Stores all external capabilities that have been revoced. For each such capability there is a `au:revokedCapability` with at least a field `cid` that holds the capability ID. Optionally there is an `nva` field, Not Valid After, copied from the original capability, that indicates when this revoked capability can be cleaned up because the original is no longer valid.

### /data/au:access/au:unusedCapabilities

This is an optional area to store capabilities that  are valid but currently not used, and that have no owner.

### /data/au:access/au:sharedKeys

Stores symmetric keys shared between Igor and a single external party. These keys are used to sign outgoing capabilities (and check incoming capabilities). Each key is stored in an `au:sharedKey` element with the following fields:

* `iss` Issuer.
* `aud` (optional) Audience.
* `sub` (optional) Subject.
* `externalKey` Symmteric key to use.

Keys are looked up either by the combination of _iss_ and _aud_ (for outgoing keys) or _iss_ and _sub_ (for incoming keys).

**NOTE** The `externalKey` data here is truly secret (it is a shared key). Therefore, this data should be moved out of the database and stored externally, really. To be fixed.

### /data/identities

Capabilities carried by all users that are logged in. Contains at least:

- get(descendent-or-self), /data/people

### /data/identities/admin

User that holds the master capabilities, capabilities with fairly unlimited access from which more limited capabilities are descended (through delegation).

There are at least the following capabilities, of which most other capabilities are descended (through delegation and narrowing the scope):

- get(descendant-or-self)+put(descendant-or-self)+post(descendant)+delete(descendant), /data
- get(descendant), /action
- get(descendant), /internal
- an empty capability (no rights, no object) with `cid=root` and no parent. This is the root of the capability tree.

### /data/identities/_user_

Capabilities this user will carry when logged in. Contains at least:

- get(descendent-or-self)+put(descendent)+post(descendent)+delete(descendent), /data/identities/_user_
- put(descendent)+post(descendent)+delete(descendent), /data/people/_user_

### /data/actions

Capabilities that are carried by all actions. Contains at least:

- get(descendant), /plugin
- get(descendant), /pluginscripts
- get(child), /action

### /data/actions/action

Capabilities this action will carry when executing.

### /data/plugindata/_pluginname_/au:capability

Capabilities this plugin will carry when executing.

## Capability consistency checks

Capabilities need to be checked for consistency, and for adherence to the schema. 

The following checks are needed as a first order check, and ensure the base infrastructure for the schema is in place:

- `/data/au:access` exists.
- `/data/au:access/au:defaultCapabilities` exists.
- `/data/au:access/au:exportedCapabilities` exists.
- `/data/au:access/au:revokedCapabilities` exists.
- `/data/au:access/au:unusedCapabilities` exists.
- `/data/au:access/au:sharedKeys` exists.
- `/data/identities` exists.
- `/data/identities/admin` exists.
- `/data/identities/admin/au:capability[cid='0']` exists.
- `/data/actions` exists.

As a second check we test that the default set of capabilities (as per the schema above) exist and are in their correct location.

As a third check we enumerate all capabilities and check the following assertions. These ensure that the tree of all capabilities is consistent:

-  Each capability must have a `cid`. 
-  This `cid` must be unique.
- Each capability (except `cid=0`) must have an existing `parent`, if not the capability is given `parent=0`.
- Each capability must have its `cid` listed in the parent `child` fields. If not it is added.
- Each `child` of each capability must exist. If not the `child` is removed.

As a fourth check we check that every capability is in an expected location. In other words, the DOM parent of the capability is one of:

- Any of the containers in the first check, or
- `/data/identities/*`
- `/data/plugindata/*`
- `/data/actions/action`

Capabilities that fail this check are moved into `/data/au:access/au:unusedCapabilities`.

## Capability actions on agent changes

To be determined what is needed when adding/removing/changing users, plugins and actions. 

Also to be determined whether anything needs to be done when adding/removing/changing services, sensors or devices.

Clearly the capabilities in the schema section will need to be added when users are added, but there is probably more (such as adding external access capabilities when a new device is added).