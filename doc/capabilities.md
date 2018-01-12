# Access Control schema

For the time being, data pertaining to access control is stored in the main database, with an XML namespace of `http://jackjansen.nl/igor/authentication` (usually encoded with the `xmlns:au` prefix).

Eventually this data will be hidden from normal Igor access, or moved to a separate database.

## Capability structure

A capability is stored in an `au:capability` element with the following children:

* `comment` textual description, to keep us sane during development.
* `xpath` an xpath referencing a single element (or a nonexisting element with a single expsiting parent element) to which this capability refers.
* `get` Together with `xpath` defines on which elements this capability grants `GET` rights:
	* empty (or non-existent): none.
	* `self` the element itself only.
	* `descendant-or-self` the whole subtree rooted at the element (the element itself, its children, its grandchildren, etc).
	* `descendant` the whole subtree rooted at the element except the element itself.
	* `child` direct children of the element.
	* More values may be added later.
* `put` Together with `xpath` defines on which elements this capability grants `PUT` rights. Values as for `get`.
* `post` Together with `xpath` defines on which elements this capability grants `POST` rights. Values as for `get`.
* `delete` Together with `xpath` defines on which elements this capability grants `DELETE` rights. Values as for `get`.
* `externalKey` (temporary, see _Open issues_ below) sign with this key when storing as a JWT in `Authentication: Bearer`.
* Crypto-based checking attributes will be added later.
* Conditions (such as capability lifetime) will be added later.

## Open issues

* How do we store multiple capabilities? 
	* As a list of capabilitities? With its own `<au:capabilitList>` tag or simply collected by enumerating all capabilities?
	* By allowing recursive `<au:capability>`?
* Can we have a reference to a capability (in stead of requiring copying) in the database?
	* By Xpath?
	* An `<name>` field?
	* Or `xml:id` or something like that?
* Crypto protection of external capabilities requires a service (REST endpoint) that can supply the public key corrsponding to the private key this Igor used to sign.
* Delegation and revocation will need to be handled.
* There seems to be no reason to give internal capabilities an identity, but that may change for external capabilities (especially in the light of revocation).
* I'm not convinced the _Subject_ in the original paper serves a purpose for us. To be seen.
* The internal representation sketched above follows Igor schema philosophy. We may switch to the schema of the original paper, and we may do so only externally.
* External representation might also be binary (for efficiency).

## Database schema additions

### /data/identities/_user_/au:capability

Capabilities this user will carry when logged in.

### /data/actions/action/au:capability

Capabilities this action will carry when executing.

### /data/plugindata/_pluginname_/au:capability

Capabilities this plugin will carry when executing.

### /data/au:access/au:defaultCapabilities


Capabilities that will be used for any request that has no `Authentication: Bearer` header, or actions, users or plugins that do not have their capabilities specified. 
