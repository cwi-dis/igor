# editData - edit entries in the database

This plugin is an absolutly minimal data editor. It allows you to inspect
any item in the database (in rather unreadable XML form) and to update it.

You can only view and edit items for which you have permission, so you may
have to login as *admin*.

You cannot edit items that have any hidden content (such as capabilities
or plugin ownership annotations) because these would get lost. If you
really need to edit such subtrees you should stop Igor and edit the database
with a text editor.
