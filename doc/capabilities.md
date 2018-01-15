# Access Control schema

For the time being, data pertaining to access control is stored in the main database, with an XML namespace of `http://jackjansen.nl/igor/authentication` (usually encoded with the `xmlns:au` prefix).

Eventually this data will be hidden from normal Igor access, or moved to a separate database.

## Capability structure

A capability is stored in an `au:capability` element.

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

Capabilities that have an external representation may have a few extra fields:

* `iss` Issuer of this capability. Usually the URL of `/issuer` on this igor.
* `aud` Audience of this capability. Required for capabilities that Igor will encode as a JWT in an outgoing `Authentication: Bearer` header.
* `sub` Subject of this capability. Required for capabilities that Igor receives as JWT in an incoming `Authentication: Bearer` header.
* For outgoing capabilities there may be other fields that are meaningful to the _audience_ of the capability. For example, a capability for a _Iotsa_ device will contain a `right` field.

External capabilities are protected using a symmetric key that is shared between Issuer and Audience (for outgoing capabilities) or Issuer and Subject (for incoming keys). This key is used to sign the JWT.

## Open issues

* How do we store multiple capabilities? 
	* As a list of capabilitities? With its own `<au:capabilitList>` tag or simply collected by enumerating all capabilities?
	* By allowing recursive `<au:capability>`?
* Can we have a reference to a capability (in stead of requiring copying) in the database?
	* By Xpath?
	* An `<name>` field?
	* Or `xml:id` or something like that?
* The symmetric protection is still tied too much with Igor also being the issuer. Needs to be fixed.
* Delegation and revocation will need to be handled.
* There seems to be no reason to give internal capabilities an identity, but that may change for external capabilities (especially in the light of revocation).

* The internal representation sketched above follows Igor schema philosophy. We may switch to the schema of the original paper, and we may do so only externally.

## Database schema additions

### /data/identities/_user_/au:capability

Capabilities this user will carry when logged in.

### /data/actions/action/au:capability

Capabilities this action will carry when executing.

### /data/plugindata/_pluginname_/au:capability

Capabilities this plugin will carry when executing.

### /data/au:access/au:defaultCapabilities

Capabilities that will be used for any request that has no `Authentication: Bearer` header, or actions, users or plugins that do not have their capabilities specified. 

### /data/au:access/au:sharedKeys

Stores symmetric keys shared between Igor and a single external party. These keys are used to sign outgoing capabilities (and check incoming capabilities). Each key is stored in an `au:sharedKey` element with the following fields:

* `iss` Issuer.
* `aud` (optional) Audience.
* `sub` (optional) Subject.
* `externalKey` Symmteric key to use.

Keys are looked up either by the combination of _iss_ and _aud_ (for outgoing keys) or _iss_ and _sub_ (for incoming keys).