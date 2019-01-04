# iotsaDiscovery - discover and initialize iotsa devices

This plugin is primarily a set of user interfaces to discover and initialize new iotsa-based devices (see <https://github.com/cwi-dis/iotsa> for examples).

The main UI page allows discovering uninitialized iotsa devices (which setup a private WiFi network with a network name that follows a known pattern) and initialized iotsa devices on the WiFi network (which advertise their existence through mDNS/Bonjour/Rendezvous).

You can then select a device and examine what sort of device it is, and what services it provides. You can also change the configuration of the device.

Specifically, iotsaDiscovery helps you to install a key and certificate into the device (so HTTPS works without warning messages about unknown certificates). And it helps you to install the Igor Issuer shared secret key, so that the device knows it can trust Igor capabilities.