"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os
import json
import urllib
import socket

from builtins import object
class ActionsPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
        
        
    def _list(self, creator=None, callerToken=None):
        """Return list of current actions, as tuple of (message, dict of xpath:description)."""
        rv = {}
        path = "actions/action"
        if creator:
            path += "[creator='{}']".format(creator)
        try:
            allActions = self.igor.databaseAccessor.get_key(path, 'application/x-python-object', 'multi', callerToken)
        except self.igor.app.getHTTPError() as e:
            rv['message'] = "Error listing actions: {}".format(self.igor.app.stringFromHTTPError(e))
        else:
            assert isinstance(allActions, dict)
            rv.update(allActions)
        return rv
        
    def _get(self, xpath, callerToken):
        """Return a single action. Returns dict {message, xpath, description}"""
        rv = {}
        try:
            rv['description'] = self.igor.databaseAccessor.get_key(xpath, 'application/x-python-object', None, callerToken)
            rv['xpath'] = xpath
        except self.igor.app.getHTTPError() as e:
            rv['message'] = "Error getting action {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
        return rv
        
    def _post(self, description, callerToken):
        """Add a new action"""
        rv = {}
        try:
            xpath = self.igor.databaseAccessor.put_key('actions/action', "text/plain", "ref", description, "application/x-python-object", callerToken, replace=False)
            if hasattr(xpath, 'get_data'): xpath = xpath.get_data()
            if hasattr(xpath, 'decode'): xpath = xpath.decode('utf8')
            xpath = xpath.strip()
        except self.igor.app.getHTTPError() as e:
            rv['message'] = "Error adding action: {}".format(self.igor.app.stringFromHTTPError(e))
        else:
            try:
                rv['description'] = self.igor.databaseAccessor.get_key(xpath, 'application/x-python-object', None, callerToken)
                rv['xpath'] = xpath
            except self.igor.app.getHTTPError() as e:
                rv['message'] = "Error getting action {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
            self.igor.internal.save(callerToken) # xxxjack should not be needed, but it seems it is...
        return rv
        
    def _replace(self, xpath, description, callerToken):
        """Replace an existing action"""
        rv = {}
        if not 'url' in description:
            return dict(message="Ill-formatted action, should contain url")
        try:
            xpath = self.igor.databaseAccessor.put_key(xpath, "text/plain", "ref", description, "application/x-python-object", callerToken, replace=True)
            if hasattr(xpath, 'get_data'): xpath = xpath.get_data()
            if hasattr(xpath, 'decode'): xpath = xpath.decode('utf8')
            xpath = xpath.strip()
        except self.igor.app.getHTTPError() as e:
            rv['message'] = "Error replacing {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
        else:
            try:
                rv['description'] = self.igor.databaseAccessor.get_key(xpath, 'application/x-python-object', None, callerToken)
                rv['xpath'] = xpath
            except self.igor.app.getHTTPError() as e:
                rv['message'] = "Error getting action {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
            self.igor.internal.save(callerToken) # xxxjack should not be needed, but it seems it is...
        return rv
        
def igorPlugin(igor, pluginName, pluginData):
    return ActionsPlugin(igor, pluginName, pluginData)
