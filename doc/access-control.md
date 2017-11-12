# Access Control Implementation

_(version of 12-Nov-2017)_

The Igor access control implementation falls apart into two distinct areas:

- _mechanism_, how Igor implements that it is possible to check that a certain operation can proceed on a certain object in the current circumstances, and
- _policy_, the actual checking.

This document is about the _mechanism_, the _policy_ is the subject of Pauline's research.

## Mechanism API

Three types of objects are involved in the access checking mechanism. The whole implementation is in the module `igor.access`. This module will eventually contain the policy implementation as well (to replace the current strawman policy).

The naming of API elements (specifically the use of _token_) reflects our current thinking about policy direction but is by no means limiting: a token could just as easily contain an _identity_ and _token checking_ would then be implemented as _ACL checking_.

But, of course, the API may change to accomodate the policy.

### Object Structure

The main object is a singleton object `igor.access.singleton` of class `Access`. This object is used by all other modules to obtain tokes and token checkers. It is a singleton because the database is a singleton too.

Tokens are represented by instances of the `AccessToken` class (or classes with the same API). An `AccessToken` can represent an actual token (supplied by an incoming HTTP request or picked up by an Igor _action_ for outgoing or internal requests), but there are also special implementations for _"No token supplied"_ and _"Igor itself"_. The latter is used, for example, when Igor updates its _last boot time_ variable, and has no external representation.

Tokens are checked by instances of the `AccessChecker` class. Whenever _any_ operation on _any_ object is attempted an access checker for that object is instantiated. It is passed the _token_ accompanying the operation, and decides whether the operation is allowed.

### Integration

Integration with the rest of Igor is very simple. All database access methods require a _token_ parameter, and before returning any XML element (or the value from any XML element, or before modifying or deleting the XML element) they obtain an _AccessChecker_ for the object. The operation only proceeds if the _AccessChecker_ allows it.

> As of this writing access checking is not fully implemented for XPath functions yet, so it is theoretically possible to obtain data from an element by not accessing the element directly but by passing it through an XML function. This will be addressed later.

The higher level API calls also all have a _token_ parameter, and usually simply pass the token on to the lower layers.

At the top level of incoming HTTP requests the token is obtained from the HTTP headers (or something similar).

At the top level of _action_ firing the token is obtained from the action description in the database (possibly indirectly).

> There is a bit of _policy_ here: it may turn out we want to carry the original token that caused the action to fire, or maybe a token representing the union of the two tokens.

Plugins are similar to actions, they can also carry their own token.

### Access Interface

The `Access` object has four methods:

- `checkerForElement(element)` returns an `AccessChecker` instance for the given XML element. The intention is that this checker can be cached (for example as a hidden pointer on the XML element implementation) as long as it is deleted when the access policies for the element change.
- `tokenForRequest(headers)` returns an `AccessToken` for an incoming HTTP request.
- `tokenForIgor()` returns a special token for internal Igor operations.
- `tokenForPlugin(name)` returns a token for the plugin with the given name. _(this API is expected to change)_
- `tokenForAction(element)` returns the token for the action whose XML element is passed in.

### AccessToken interface

The `AccessToken` object has one method:

- `addToHeaders(headers)` called when a token should be carried on an outgoing HTTP request. If the token has a valid externl representation it adds that representation to the `headers` dictionary.  _(this API is expected to change)_

### AccessChecker interface

The `AccessChecker` object has one method:

- `allowed(operation, token)` return `True` if `token` (which is an `AccessToken`) has the right to execute `operation`. Currently `operation` is a string with the following possible values:
	- `'get'` (read the element)
	- `'put'` (modify the element)
	- `'post'` (to create children elements)
	- `'delete'` (remove the element)
	- `'run'` (run the action or plugin)
	- 