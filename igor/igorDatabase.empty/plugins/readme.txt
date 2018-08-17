You can put plugins (either copied or symlinked) here after installing
your Igor database.

A plugin foo is a directory which can contain:
- a module foo.py declaring a function foo(), 
  which is run when accessing http://igorhost/plugin/foo
- a subdirectory scripts, where a script bar is ran when accessing
  http://igorhost/pluginscript/foo/bar.

A file database-fragment.xml should be merged into the database manually
(for now).

Any other files are ignored (but available to the plugin module and the
plugin scripts).
