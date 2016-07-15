bleServer
=========

This little server keeps track of which Bluetooth LE devices are in range.
For each device it remembers when it was first seen (and for devices that
are no longer available when it was last seen).
Access as http://localhost:8080/ble (or modify on the command line)

Setup
-----

This server should run on any Linux, but was tested with Raspberry Pi 2 and 3.
First setup your bluetooth. If "hciconfig" shows you a "hci0" interface
this already works. Otherwise for RPi3 read http://www.cnet.com/how-to/how-to-setup-bluetooth-on-a-raspberry-pi-3/
and for RPi2 with external Bluetooth LE adapter read http://www.elinux.org/RPi_Bluetooth_LE

If you want to run bleServer at boot: read and possibly edit initscript-bleServer,
move it to /etc/init.d/bleServer, run "sudo update-rc.d bleServer defaults" and
reboot.
