from __future__ import unicode_literals

AU_NAMESPACE = {
    "au":"http://jackjansen.nl/igor/authentication",
}

NAMESPACES = { 
    "au":"http://jackjansen.nl/igor/authentication",
    "own":"http://jackjansen.nl/igor/owner",
     }

NORMAL_OPERATIONS = {'get', 'put', 'post', 'delete'}
AUTH_OPERATIONS = {'delegate'}
ALL_OPERATIONS = NORMAL_OPERATIONS | AUTH_OPERATIONS

CASCADING_RULES = {'self', 'descendant', 'descendant-or-self', 'child'}
CASCADING_RULES_IMPLIED = {
    'self' : {'self'},
    'descendant' : {'descendant', 'child'},
    'descendant-or-self' : {'self', 'descendant', 'descendant-or-self', 'child'},
    'child' : {'child'}
}

DEBUG=[]    # False, but trick in __main__ can make it true even though imported as * by other modules
DEBUG_DELEGATION=False

# For the time being: define this to have the default token checker allow everything
# the dummy token allows
DEFAULT_IS_ALLOW_ALL=True

class AccessControlError(ValueError):
    pass

