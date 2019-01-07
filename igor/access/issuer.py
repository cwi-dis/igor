from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
# Access control
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import random
import urllib.parse
import os
import jwt

from .vars import *
from .capability import *
from .checker import *
from .consistency import *
from .. import xmlDatabase

_accessSelfToken = None # Set by __init__ after importing

class IssuerInterface(object):
    """Implement interface to the issuer"""
    def __init__(self):
        self._self_audience = None
        self._shadowDatabase = None
        
    def _initIssuer(self, now=False):
        """Initialize the issuer, may op its private database."""
        if not self._shadowDatabase:
            shadowFilename = os.path.join(self.igor.pathnames.datadir, 'shadow.xml')
            if os.path.exists(shadowFilename):
                self._shadowDatabase = xmlDatabase.DBImpl(shadowFilename)
            else:
                print('Warning: secret keys in main database, no shadow database {}'.format(shadowFilename))
                if now:
                    self._shadowDatabase = self.igor.database
        return

    def getSelfAudience(self, token=None):
        """Return an audience identifier that refers to us"""
        if not self._self_audience:
            baseUrl = self.igor.database.getValue('services/igor/url', _accessSelfToken)
            self._self_audience = urllib.parse.urljoin(baseUrl, '/')
        return self._self_audience

    def getSelfIssuer(self, token=None):
        """Return URL for ourselves as an issuer"""
        return urllib.parse.urljoin(self.getSelfAudience(),  '/issuer')

    def _getSharedKey(self, iss=None, aud=None):
        """Get secret key shared between issuer and audience"""
        self._initIssuer(now=True)
        if iss is None:
            iss = self.getSelfIssuer()
        if aud is None:
            aud = self.getSelfAudience()
        keyPath = "au:access/au:sharedKeys/au:sharedKey[iss='%s'][aud='%s']/externalKey" % (iss, aud)
        externalKey = self._shadowDatabase.getValue(keyPath, _accessSelfToken, namespaces=NAMESPACES)
        if not externalKey:
            print('access: _getExternalRepresentation: no key found at %s' % keyPath)
            self.igor.app.raiseHTTPError('404 No shared key found for iss=%s, aud=%s' % (iss, aud))
        return externalKey

    def _decodeIncomingData(self, data):
        sharedKey = self._getSharedKey()
        if DEBUG: 
            print('access._decodeIncomingData: %s: externalRepresentation %s' % (self, data))
            print('access._decodeIncomingData: %s: externalKey %s' % (self, sharedKey))
        try:
            content = jwt.decode(data, sharedKey, issuer=self.getSelfIssuer(), audience=self.getSelfAudience(), algorithms=['RS256', 'HS256'])
        except jwt.DecodeError:
            print('access: ERROR: incorrect signature on bearer token %s' % data)
            print('access: ERROR: content: %s' % jwt.decode(data, verify=False))
            self.igor.app.raiseHTTPError('400 Incorrect signature on key')
        except jwt.InvalidIssuerError:
            print('access: ERROR: incorrect issuer on bearer token %s' % data)
            print('access: ERROR: content: %s' % jwt.decode(data, verify=False))
            self.igor.app.raiseHTTPError('400 Incorrect issuer on key')
        except jwt.InvalidAudienceError:
            print('access: ERROR: incorrect audience on bearer token %s' % data)
            print('access: ERROR: content: %s' % jwt.decode(data, verify=False))
            self.igor.app.raiseHTTPError('400 Incorrect audience on key')
        if DEBUG: 
            print('access._decodeIncomingData: %s: tokenContent %s' % (self, content))
        return content

    def _encodeOutgoingData(self, tokenContent):
        iss = tokenContent.get('iss')
        aud = tokenContent.get('aud')
        # xxxjack Could check for multiple aud values based on URL to contact...
        if not iss or not aud:
            print('access: _getExternalRepresentation: no iss and aud, so no external representation')
            self.igor.app.raiseHTTPError('404 Cannot lookup shared key for iss=%s aud=%s' % (iss, aud))
        externalKey = self._getSharedKey(iss, aud)
        externalRepresentation = jwt.encode(tokenContent, externalKey, algorithm='HS256')
        externalRepresentation = externalRepresentation.decode('ascii')
        if DEBUG: 
            print('access._encodeOutgoingData: %s: tokenContent %s' % (self, tokenContent))
            print('access._encodeOutgoingData: %s: externalKey %s' % (self, externalKey))
            print('access._encodeOutgoingData: %s: externalRepresentation %s' % (self, externalRepresentation))
        return externalRepresentation
        
    def getSubjectList(self, token=None):
        """Return list of subjects that trust this issuer"""
        # xxxjack should perform some checks on token
        self._initIssuer(now=True)
        assert self.igor
        assert self.igor.database
        # xxxjack this is wrong: it also returns keys shared with other issuers
        subjectValues = self._shadowDatabase.getValues('au:access/au:sharedKeys/au:sharedKey/sub', _accessSelfToken, namespaces=NAMESPACES)
        subjectValues = [x[1] for x in subjectValues]
        subjectValues = list(subjectValues)
        subjectValues.sort()
        return subjectValues

    def getAudienceList(self, token=None):
        """Return list of audiences that trust this issuer"""
        # xxxjack should perform some checks on token
        self._initIssuer(now=True)
        audienceValues = self._shadowDatabase.getValues('au:access/au:sharedKeys/au:sharedKey/sub', _accessSelfToken, namespaces=NAMESPACES)
        audienceValues = set(audienceValues)
        audienceValues = list(audienceValues)
        audienceValues.sort()
        return audienceValues
        
    def getKeyList(self, token=None):
        """Return list of tuples with (iss, sub, aud) for every key"""
        # xxxjack should perform some checks on token
        assert self.igor
        assert self.igor.database
        self._initIssuer(now=True)
        keyElements = self._shadowDatabase.getElements('au:access/au:sharedKeys/au:sharedKey', 'get', _accessSelfToken, namespaces=NAMESPACES)
        rv = []
        for kElement in keyElements:
            iss = self.igor.database.getValue('iss', _accessSelfToken, namespaces=NAMESPACES, context=kElement)
            aud = self.igor.database.getValue('aud', _accessSelfToken, namespaces=NAMESPACES, context=kElement)
            sub = self.igor.database.getValue('sub', _accessSelfToken, namespaces=NAMESPACES, context=kElement)
            kDict = dict(aud=aud)
            if iss:
                kDict['iss'] = iss
            if sub:
                kDict['sub'] = sub
            rv.append(kDict)
        return rv
        
    def getSecretKeysForAudience(self, aud, token=None):
        """Return verbatim secret key for this audience"""
        # xxxjack should perform some checks on token
        try:
            keyData = self._getSharedKey(aud=aud)
        except self.igor.app.getHTTPError():
            return []
        return [(self.getSelfIssuer(), keyData)]
        
        
    def createSharedKey(self, sub=None, aud=None, token=None):
        """Create a secret key that is shared between issues and audience"""
        assert self.igor
        assert self.igor.database
        self._initIssuer(now=True)
        iss = self.getSelfIssuer()
        if not aud:
            aud = self.getSelfAudience()
        keyPath = "au:access/au:sharedKeys/au:sharedKey[iss='%s'][aud='%s']" % (iss, aud)
        if sub:
            keyPath += "[sub='%s']" % sub
        keyElements = self._shadowDatabase.getElements(keyPath, 'get', _accessSelfToken, namespaces=NAMESPACES)
        if keyElements:
            self.igor.app.raiseHTTPError('409 Shared key already exists')
        keyBits = 'k' + str(random.getrandbits(64))
        keyData = dict(iss=iss, aud=aud, externalKey=keyBits)
        if sub:
            keyData['sub'] = sub
        parentElement = self._shadowDatabase.getElements('au:access/au:sharedKeys', 'post', _accessSelfToken, namespaces=NAMESPACES)
        if len(parentElement) != 1:
            if DEBUG_DELEGATION: print('access: createSharedKey: no unique destination au:access/au:sharedKeys')
            self.igor.app.raiseNotfound()
        parentElement = parentElement[0]
        element = self._shadowDatabase.elementFromTagAndData("sharedKey", keyData, namespace=AU_NAMESPACE)
        parentElement.appendChild(element)
        self._shadowDatabase.saveFile()
        return keyBits
        
    def deleteSharedKey(self, iss=None, sub=None, aud=None, token=None):
        """Delete a shared key"""
        self._initIssuer(now=True)
        if not iss:
            iss = self.getSelfIssuer()
        if not aud:
            aud = self.getSelfAudience()
        keyPath = "au:access/au:sharedKeys/au:sharedKey[iss='%s'][aud='%s']" % (iss, aud)
        if sub:
            keyPath += "[sub='%s']" % sub
        self._shadowDatabase.delValues(keyPath, _accessSelfToken, namespaces=NAMESPACES)
        self._shadowDatabase.saveFile()
        return ''
        
