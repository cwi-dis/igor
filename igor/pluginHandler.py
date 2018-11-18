from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals
from builtins import str
from past.builtins import basestring
from builtins import object
import os
import sys
import subprocess
import imp

class IgorPlugins(object):
    """Class to handle access to plugins"""
    
    def __init__(self, igor):
        self.igor = igor

    def _is_venv(self):
        """Return True if we are in a virtual env"""
        return (hasattr(sys, 'real_prefix') or
                (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))

    def _getPluginObject(self, pluginName, token=None):
        """Import the plugin, call the factory function and return the object for pluginName"""
        #
        # Import plugin as a submodule of igor.plugins
        #
        import igor.plugins # Make sure the base package exists
        moduleName = 'igor.plugins.'+pluginName
        if moduleName in sys.modules:
            # Imported previously.
            pluginModule = sys.modules[moduleName]
        else:
            # New. Try to import.
            moduleDir = os.path.join(self.igor.pathnames.plugindir, pluginName)
            try:
                mfile, mpath, mdescr = imp.find_module('igorplugin', [moduleDir])
                pluginModule = imp.load_module(moduleName, mfile, mpath, mdescr)
            except ImportError:
                print('------ import failed for', pluginName)
                traceback.print_exc()
                print('------')
                self.igor.app.raiseNotfound(404)
            pluginModule.IGOR = self.igor

        # xxxjack need to check that the incoming action is allowed on this plugin
        # Get the token for the plugin itself
        pluginToken = self.igor.access.tokenForPlugin(pluginName, token=token)
    
        # Find plugindata and per-user plugindata
        pluginData = self._getPluginData(pluginName, pluginToken)
        try:
            factory = getattr(pluginModule, 'igorPlugin')
        except AttributeError:
            self.igor.app.raiseHTTPError("501 Plugin %s problem: misses igorPlugin() method" % (pluginName))
        #
        # xxxjack note that the following set of globals basically exports the
        # whole object hierarchy to plugins. This means that a plugin has
        # unlimited powers. This needs to be fixed at some time, so plugin
        # can come from untrusted sources.
        #
        pluginObject = factory(self.igor, pluginName, pluginData)
        return pluginObject

    def _getPluginScriptDir(self, pluginName, token=None):
        """Return directory with scripts for pluginName"""
        return os.path.join(_SERVER.igor.pathnames.plugindir, pluginName, 'scripts')

    def _getPluginData(self, pluginName, token=None):
        """Return plugin data for pluginName"""
        try:
            pluginData = self.igor.databaseAccessor.get_key('plugindata/%s' % (pluginName), 'application/x-python-object', 'content', token)
        except self.igor.app.getHTTPError():
            pluginData = {}
        return pluginData
        
    def _getPluginUserData(self, pluginName, userName, token=None):
        """Return per-user data for this plugin or None"""
        try:
            userData = self.igor.databaseAccessor.get_key('identities/%s/plugindata/%s' % (userName, pluginName), 'application/x-python-object', 'content', token)
        except self.igor.app.getHTTPError():
            userData = {}
        return userData
        
    def update(self, token=None):
        """Install (or re-install) plugin-specific portions of the database"""
        checker = self.igor.access.checkerForEntrypoint('/filesystem')
        if not checker.allowed('get', token):
            return
        allOK = True
        allFNs = os.listdir(self.igor.pathnames.plugindir)
        allNewPlugins = []
        for fn in allFNs:
            if fn[-4:] == '.xml':
                pluginName = fn[:-4]
                if os.path.exists(os.path.join(self.igor.pathnames.plugindir, pluginName)):
                    allNewPlugins.append(pluginName)
                else:
                    print('Warning: found XML fragment but no corresponding plugin: %s' % fn)
        for newPlugin in allNewPlugins:
            ok = self._installPluginFragment(newPlugin, token)
            if not ok:
                allOK = False
        # xxxjack should also install requirements, probably...
        if allOK:
            return 'OK'
        return 'Error during plugin fragment installation, please check logfile'
       
    def _installPluginFragment(self, pluginName, token):
        """Install XML fragment for a specific plugin"""
        pluginFile = os.path.join(self.igor.pathnames.plugindir, pluginName + '.xml')
        print('Merging plugin fragment %s' % pluginFile)
        fp = open(pluginFile)
        pluginData = fp.read()
        fp.close()
        pluginTree = self.igor.database.elementFromXML(pluginData)
        self.igor.database.mergeElement('/', pluginTree, token=token, plugin=True)
        os.unlink(pluginFile)
        self.igor.save(token=self.igor.access.tokenForIgor())
        return True
        
    def installstd(self, pluginName=None, stdName=None, token=None):
        checker = self.igor.access.checkerForEntrypoint('/filesystem')
        if not checker.allowed('get', token):
            return
        if not pluginName:
            self.igor.app.raiseNotFound()
        if not stdName:
            stdName = pluginName
        if not os.path.exists(os.path.join(self.igor.pathnames.stdplugindir, stdName)):
            self.igor.app.raiseNotFound()
        # Create the symlink to the plugin
        dst = os.path.join(self.igor.pathnames.plugindir, pluginName)
        src = os.path.join('..', 'std-plugins', stdName)
        os.symlink(src, dst)
        # Create the xmlfragment, if needed
        xmlfrag = os.path.join(dst, 'database-fragment.xml')
        if os.path.exists(xmlfrag):
            fp = open(xmlfrag)
            fragData = fp.read()
            fp.close()
            fragData = fragData.replace('{plugin}', pluginName)
            fragDest = dst + '.xml'
            fp = open(fragDest, 'w')
            fp.write(fragData)
            fp.close()
            self._installPluginFragment(pluginName, token)
        requirementsFile = os.path.join(dst, 'requirements.txt')
        if os.path.exists(requirementsFile):
            if self._is_venv():
                pip_cmd = [sys.executable, '-m', 'pip', 'install']
            else:
                pip_cmd = [sys.executable, '-m', 'pip', 'install', '--user']
            sts = subprocess.call(pip_cmd + ['-r', requirementsFile])
            if sts != 0:
                self.igor.app.raiseHTTPError('500 Installing requirements for plugin returned error %d' % sts)
        return ''
        
    def install(self, pluginname=None, zipfile=None, token=None):
        self.igor.app.raiseHTTPError('500 Not yet implemented')
    
    def uninstall(self, pluginName=None, token=None):
        checker = self.igor.access.checkerForEntrypoint('/filesystem')
        if not checker.allowed('get', token):
            return
        dst = os.path.join(self.igor.pathnames.plugindir, pluginName)
        os.unlink(dst)
        # And remove all elements pertaining to the plugin
        xp = '//*[@own:plugin="%s"]' % pluginName
        self.igor.database.delValues(xp, token)
        self.igor.save(token=self.igor.access.tokenForIgor())
        return ''
        
    def list(self, token=None):
        allFNs = os.listdir(self.igor.pathnames.plugindir)
        allPlugins = []
        for fn in allFNs:
            if '.' in fn or '@' in fn or '~' in fn or fn[:2] == '__':
                continue
            allPlugins.append(fn)
        return allPlugins
        
    def liststd(self, token=None):
        allFNs = os.listdir(self.igor.pathnames.stdplugindir)
        allPlugins = []
        for fn in allFNs:
            if '.' in fn or '@' in fn or '~' in fn or fn[:2] == '__':
                continue
            allPlugins.append(fn)
        allPlugins.sort()
        return allPlugins
        
    def exists(self, pluginName, token=None):
        return os.path.isdir(os.path.join(self.igor.pathnames.plugindir, pluginName))
        
    def info(self, pluginName, token=None):
        pluginPath = os.path.join(self.igor.pathnames.plugindir, pluginName)
        if not os.path.isdir(pluginPath):
            return None
        isStd = os.path.islink(pluginPath)
        rv = dict(name="pluginName", std=isStd)
        if isStd:
            rv['stdName'] = os.path.basename(os.path.realpath(pluginPath))
        if os.path.exists(os.path.join(pluginPath, 'readme.md')):
            rv['doc'] = '/plugin/%s/page/readme.md' % pluginName
        pages = []
        for fname in os.listdir(pluginPath):
            if fname[-5:] == '.html' and fname[:1] != '_':
                pages.append('/plugin/%s/page/%s' % (pluginName, fname))
        rv['pages'] = pages
        pluginData = self.igor.databaseAccessor.get_key('plugindata/%s' % pluginName, 'application/x-python-object', 'multi', token)
        if pluginData:
            rv['pluginData'] = list(pluginData.keys())[0]
        userData = []
        userData = self.igor.databaseAccessor.get_key('identities/*/plugindata/%s' % pluginName, 'application/x-python-object', 'multi', token)
        rv['userData'] = list(userData.keys())
        return rv
