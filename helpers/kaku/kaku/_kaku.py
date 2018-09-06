from __future__ import unicode_literals
from builtins import object
__author__ = 'erik@precompiled.com'

import usb.core
import usb.util


class TPC300(object):
    """
    This is the pure Python implementation of the TPC300 class.
    While the Windows version uses the TCP300A.DLL that can be
    downloaded, this version sends raw instructions to the USB
    port using pyUSB 1.x.
    It should be usable in any Python environment as it is
    pure Python code, but I found that usb.core.find() does not
    return any USB devices in Windows.
    """
    def __init__(self):
        # find our device - does not seem to work in Windows...
        self.dev = usb.core.find(idVendor=0xFEFF, idProduct=0x0802)

        # was it found?
        if self.dev is None:
            raise ValueError('TPC300 USB Device not found')

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        if self.dev.is_kernel_driver_active(0) is True:
                self.dev.detach_kernel_driver(0)
        self.dev.set_configuration()

        # get an endpoint instance: device -> config -> interface -> endpoint
        config = self.dev.get_active_configuration()
        # interfacenumber of the first config
        interface_number = config[(0,0)].bInterfaceNumber
        # get the interface
        intf = usb.util.find_descriptor(config, bInterfaceNumber = interface_number,)
        # ...and the endpoint
        self.endpoint = usb.util.find_descriptor(
            intf,
            # match the first OUT endpoint
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT
        )


    def send(self, signaltype, code, onoff):
        # bit[0] = instruction(0x5A)
        # bit[1] = code
        # bit[2] = onoff*2 + signaltype
        instruction = 90
        command = [instruction, code, signaltype + (onoff*2), 5]
        padding = [0] * (64 - len(command))
        self.endpoint.write(bytearray(command + padding))


    def scene(self, number):
        # bit[0] = instruction(0x53)
        # bit[1] = (scene -1)
        instruction = 83
        command = [instruction, number-1]
        padding = [0] * (64 - len(command))
        self.endpoint.write(bytearray(command + padding))

