This script can control the lighting with KAKU switches, from a Linux machine.
The bit sequences have been determined by trial-and-error.

This directory is a python runnable package, use "python kaku"
for (minimal) help.

The _kaku.py submodule originally comes from https://launchpad.net/pykaku.
The module needs pyusb, install with "sudo easy_install pyusb".

You also need to modify the permissions on the USB device.
Copy 99-kaku.rules to /etc/udev/rules.d and unplug and replug
the device. That should give you permission without being superuser.



