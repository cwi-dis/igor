"""Sample plugin module for Igor"""
from __future__ import unicode_literals
import requests
import os
import json
import urllib
import socket

from builtins import object
class EditDataPlugin(object):
    def __init__(self, igor, pluginName, pluginData):
        self.igor = igor
        self.pluginName = pluginName
        self.pluginData = pluginData
        
    def index(self, *args, **kwargs):
        return self.igor.app.raiseHTTPError("404 No index method for this plugin")
        
    def _get(self, xpath, token=None):
        """Get XML data for given xpath. Returns dict with message, xpath, xmldata"""
        message = ""
        xmldata = ""
        try:
            xmldata = self.igor.databaseAccessor.get_key(xpath, 'application/xml', None, token)
            if hasattr(xmldata, 'get_data'): xmldata = xmldata.get_data()
            rawxmldata = self.igor.databaseAccessor.get_key(xpath, 'application/xml', "raw", token)
            if hasattr(rawxmldata, 'get_data'): rawxmldata = rawxmldata.get_data()
        except self.igor.app.getHTTPError() as e:
            message = "Error accessing {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
        else:
            if xmldata != rawxmldata:
                message = "Element contains hidden (namespaced) data such as capabilities or ownership information. Editing is not possible."
        return dict(message=message, xpath=xpath, xmldata=xmldata)
        
    def _post(self, xpath, newData, token=None):
        """Add a new entry to the database. Returns dict with message, xpath, xmldata"""
        message = ""
        xmldata = ""
        try:
            xpath = self.igor.databaseAccessor.put_key(xpath, "text/plain", "ref", newData, "application/xml", token, replace=False)
            if hasattr(xpath, 'get_data'): xpath = xpath.get_data()
            if hasattr(xpath, 'decode'): xpath = xpath.decode('utf8')
            xpath = xpath.strip()
        except self.igor.app.getHTTPError() as e:
            message = "Error replacing {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
        else:
            xmldata = self.igor.databaseAccessor.get_key(xpath, 'application/xml', None, token)
            if hasattr(xmldata, 'get_data'): xmldata = xmldata.get_data()
        return dict(message=message, xpath=xpath, xmldata=xmldata)
        
    def _replace(self, xpath, oldData, newData, token=None):
        """Replace the value of a data item with a new one. Returns dict with message, xpath, xmldata"""
        message = ""
        xmldata = ""
        try:
            rawxmldata = self.igor.databaseAccessor.get_key(xpath, 'application/xml', "raw", token)
            if hasattr(rawxmldata, 'get_data'): rawxmldata = rawxmldata.get_data()
        except self.igor.app.getHTTPError() as e:
            message = "Error accessing {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
            return dict(message=message, xpath=xpath, xmldata=xmldata)
        if rawxmldata.strip() != oldData.strip():
            print('xxxjack new', oldData.strip())
            print('xxxjack raw', rawxmldata.strip())
            message = "Old data does not match. Element may have changed in the mean time, or it contains hidden (namespaced) data and cannot be edited."
        else:
            try:
                xpath = self.igor.databaseAccessor.put_key(xpath, "text/plain", "ref", newData, "application/xml", token, replace=True)
                if hasattr(xpath, 'get_data'): xpath = xpath.get_data()
                if hasattr(xpath, 'decode'): xpath = xpath.decode('utf8')
                xpath = xpath.strip()
            except self.igor.app.getHTTPError() as e:
                message = "Error replacing {}: {}".format(xpath, self.igor.app.stringFromHTTPError(e))
            else:
                xmldata = self.igor.databaseAccessor.get_key(xpath, 'application/xml', None, token)
                if hasattr(xmldata, 'get_data'): xmldata = xmldata.get_data()
        return dict(message=message, xpath=xpath, xmldata=xmldata)
        
def igorPlugin(igor, pluginName, pluginData):
    return EditDataPlugin(igor, pluginName, pluginData)
