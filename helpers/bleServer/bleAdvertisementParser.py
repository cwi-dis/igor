#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  7 15:50:37 2017

@author: Sergio Cabrero
@email: s.cabrero@cwi.nl
"""
from __future__ import division
from __future__ import unicode_literals
from builtins import str
from past.utils import old_div
from struct import unpack
import uuid
import binascii
# from base64 import b64encode




"""
    Main parsers
"""
def parse_packet(packet):
    pass

def parse_payload(payload):
    """This function parses only the payload of the advertisment """
    # Get all advs in packet
    allCorrect = True
    advs = {}
    while payload:
        lenByte,  = unpack('<B', payload[0:1])
        payload = payload[1:]
        # Cater for zero-lengthadvertisements
        if lenByte == 0:
            allCorrect = False
            continue
        # Get data for one single item
        singleAdvertisementItem = payload[:lenByte]
        payload = payload[lenByte:]
        # See if we can parse the item
        typeByte, = unpack("<B", singleAdvertisementItem[0:1])
        singleAdvertisementItem = singleAdvertisementItem[1:]
        if typeByte in adv_parsers:
            advKey, advParser = adv_parsers[typeByte]
            advUpdates, thisCorrect = advParser(advKey, singleAdvertisementItem)
            if not thisCorrect:
                allCorrect = False
        else:
            #allCorrect = False
            advKey = 'unknown_0x%02x' % typeByte 
            advUpdates = {advKey: binascii.hexlify(singleAdvertisementItem).decode('ascii')}
        for advKey in advUpdates:
            if advKey in advs:
                # Duplicate key!
                allCorrect = False
        advs.update(advUpdates)
    return advs, allCorrect

"""
    Advertisement parsers
"""


def parse_flags(name, payload):
    adv = {}
    correct = True
    if len(payload) != 1:
        correct = False
    bits, = unpack('<B', payload[0:1])
    if bits & 0x01: adv['le_limited_discoverable'] = True
    if bits & 0x02: adv['le_general_discoverable'] = True
    if bits & 0x04: adv['bredr_not_supported'] = True
    if bits & 0x08: adv['simultaneous_le_bredr_c'] = True
    if bits & 0x10: adv['simultaneous_le_bredr_h'] = True
    if bits & 0xe0:
        adv['raw'] = bits
        correct = False
    return {name: adv}, correct

def parse_mf_data(name, payload):
    if len(payload) < 2:
        return adv, False
    manufacturerID, = unpack('<H', payload[:2])
    if manufacturerID in mf_parsers:
        dataType, parserFunc = mf_parsers[manufacturerID]
        adv, correct = parserFunc(payload[2:])
        if correct:
            return {dataType : adv}, True
    return {name: dict(raw=binascii.hexlify(payload[2:]).decode('ascii'), manufacturerID=manufacturerID)}, True

def parse_str(name, payload):
    return {name : str(payload)}, True

adv_parsers = {0xff: ('manufacturer_specific_data', parse_mf_data),
               0x08: ('shortened_local_name', parse_str),
               0x09: ('complete_local_name', parse_str),
               0x01: ('flags', parse_flags),
               }

"""
    Manufacturer data parsers
"""


def parse_mf_ibeacon(payload):
    adv = {}
    if len(payload) != 23:
        return adv, False
    # Next two bytes seem to be apple-specific type, we only understand iBeacon.
    byte_0, byte_1 =  unpack("<BB", payload[0:2])
    if byte_0 != 0x02 or byte_1 != 0x15:
        return adv, False
    # It is an iBoeacon data item. Parse.
    adv['uuid'] = str(uuid.UUID(bytes=payload[2:18]))
    adv['major'], adv['minor'], power =  unpack(">HHb", payload[18:])
    adv['power'] = power
    return adv, True

def parse_mf_sensortag(payload):
    adv = {}
    correct = True
    adv['version'] = unpack("B", payload[0:1])[0]

    x_axis = old_div(unpack("h", payload[3:5])[0], float(old_div(32768, 2)))
    y_axis = old_div(unpack("h", payload[5:7])[0], float(old_div(32768, 2)))
    z_axis = old_div(unpack("h", payload[7:9])[0], float(old_div(32768, 2)))
    adv['accelerometer'] = {'x':x_axis, 'y': y_axis, 'z': z_axis}

    def __compute_temp(raw_temp):
        SCALE_LSB = 0.03125
        it = raw_temp >> 2

        return float(it) * SCALE_LSB

    raw_die_temp = unpack("H", payload[9:11])[0]
    adv['die_temp'] = __compute_temp(raw_die_temp)

    raw_target_temp = unpack("h", payload[11:])[0]
    adv['target_temp'] = __compute_temp(raw_target_temp)
    return adv, correct


def parse_mf_estimote(payload):
    adv = {}
    correct = True
    adv['version'] = unpack("B", payload[0:1])[0]

    adv['uuid'] = "d0d3fa86ca7645ec9bd96af4" + ''.join(x.encode("hex") for x in payload[1:5])
    adv['major'] = unpack(">H", payload[5:7])[0]
    adv['minor']  = unpack(">H", payload[7:9])[0]

    raw_temp = (unpack("<H", payload[11:13])[0] & 0x0fff) << 4

    if (raw_temp & 0x8000) != 0:
        adv['temp'] = old_div(((raw_temp & 0x7fff) - 32768), 256.0)
    else:
        adv['temp']  = old_div(raw_temp, 256.0)

    adv['is_moving'] = unpack("B", payload[13:14])[0] & 0x40 != 0

    x_axis = unpack("b", payload[14:15])[0] * 15.625 / 1000.0
    y_axis = unpack("b", payload[15:16])[0] * 15.625 / 1000.0
    z_axis = unpack("b", payload[16:17])[0] * 15.625 / 1000.0

    adv['accelerometer'] = {'x':x_axis, 'y': y_axis, 'z': z_axis}

    def __convert_motion_state(raw):
        unit = (raw >> 6) & 0x03
        duration = raw & 0x3f

        if unit == 1:
            return duration * 60
        elif unit == 2:
            return duration * 3600

        return duration

    motion = unpack("B", payload[17:18])[0]
    adv['current_motion_state'] = __convert_motion_state(motion)
    motion = unpack("B", payload[18:19])[0]
    adv['previous_motion_state'] = __convert_motion_state(motion)

    adv['voltage'] = 0

    if unpack("B", payload[13:14])[0] & 0x80 == 0:
        first_nibble = (unpack("B", payload[13:14])[0] & 0x3f) << 4
        second_nibble = unpack("B", payload[12:13])[0] & 0xf
        adv['voltage'] = (first_nibble + second_nibble) * 3.6 / 1023.0

    # DON'T KNOW IF THIS IS RIGHT
    scale_dbs = {0: -30,
                  1: -20,
                  2: -16,
                  3: -12,
                  4: -8,
                  5: -4,
                  6:  0,
                  7:  4}

    adv['power'] = int(unpack("B", payload[19:20])[0] & 0x0f)
    adv['channel'] = int(unpack("B", payload[19:20])[0] >> 4)
#    adv['rssi_1m'] = twos_comp((unpack("B", payload[19:20])[0] & 0x0f), 2), len
    return adv, correct


mf_parsers = {
           0x000D: ('cwi_sensortag', parse_mf_sensortag),
           0x004C: ('ibeacon', parse_mf_ibeacon),
           0x015D: ('nearable', parse_mf_estimote),
           }


"""
    Helper functions
"""

def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val                         # return positive value as is



def print_bytes(payload):
    return ' '.join(['%0.2X' % int(unpack("<B", b)[0]) for b in payload]).strip()
    
