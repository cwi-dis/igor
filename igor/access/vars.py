import web

NAMESPACES = { "au":"http://jackjansen.nl/igor/authentication" }

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

DEBUG=False
DEBUG_DELEGATION=True

# For the time being: define this to have the default token checker allow everything
# the dummy token allows
DEFAULT_IS_ALLOW_ALL=True


def myWebError(msg):
    return web.HTTPError(msg, {"Content-type": "text/plain"}, msg+'\n\n')

class AccessControlError(ValueError):
    pass
