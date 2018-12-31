# iirfid - read RFID tags

This plugin reads RFID tags (mifare tags, specifically) and stores all presented tags in `sensors/rfid`, sequentially. Tags that are known (by hardware address) are also stored in `sensors/tags`.

The intention of this separation is that a _tag_ is a more high-level concept (such as "Jacks keyring") that is used to trigger further actions. Tags using other methods than RFID (for example barcodes or QR-codes) would be merged here with the RFID tags, so the concept of a _tag_ becomes _a thing that can trigger actions when presented to a suitable reader_.

## requirements

The main requirement is an RFID-reader that connects to a computer using an Arduino and a USB interface. It actually requires a very specific RFID-reader of which we happen to have two lying around at CWI (constructed by Interactive Institute for a previous project), which no-one else probably has, so this plugin is more an example than anything else.

To use this plugin as the basis for support of another RFID reader: modify the script `iirfid/scripts/rfidread.py` to support the reader you have.

## schema

Some of the data is unique to the iirfid plugin, some other data (with _tags_ or _rfid_ in the name in stead of _iirfid_) is shared with other rfid reader plugins.

* `sensors/iirfidrfid`: Collects hardware unique IDs (in order of the time the tags were presented) in sub-elements:
	* `rfidtag`: 4 colon-separated hex bytes.
* `sensors/tags`: Collects "known" tags in order presented in sub-elements:
	* `tag`: human-readable name.
* `plugindata/iirfid/host`: if non-empty, host to which the RFID reader is connected (must be reachable with _ssh_ without password). String.
* `plugindata/iirfid/serial`: Serial device to which RFID reader is connected. String.
* `plugindata/iirfid/baud`: Baud rate. Integer.
* `plugindata/rfid/tag`: Maps mifare tag unique IDs to human-readable names:
	* `id`: 4 colon-separated hex bytes.
	* `name`: human readable name.

## actions

* _start_: starts the rfid reader asynchronously, telling it to POST each tag presented to this Igor, `sensors/rfid/rfidtag`.
* _cleanup_: remove all entries in `sensors/rfid` and `sensors/tags` except the last one.

## internal actions

* When a new raw tag is entered into `sensors/iirfidrfid` look it up in `plugindata/rfid` and post the user-friendly name in `sensors/tags`.
