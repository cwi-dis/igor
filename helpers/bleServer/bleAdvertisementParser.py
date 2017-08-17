#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Tue Feb  7 15:50:37 2017

@author: Sergio Cabrero
@email: s.cabrero@cwi.nl
"""
from struct import unpack
# from base64 import b64encode

# """
#     Load BLE standard identifiers
# """
def load_BLEstandard_codes(f1='data/BLE_adv_types.csv', f2='data/ManufacturerIds.csv'):
    with open(f1, 'r') as midsf:
        ADVS = {}
        for line in midsf.readlines():
            try:
                adv, name = line.strip().split('\t')
                ADVS['%0.2X' % int(adv,0)] = name
            except:
                print 'Could not process:', line

    with open(f2, 'r') as midsf:
        MID = {}
        for line in midsf.readlines():
            try:
                ln, h, company = line.strip().split('\t')
                MID['%0.4X' % int(h,0)] = company
            except:
                print 'Could not process:', line

    MID['000D'] = 'CWI Sensortag'
    return ADVS, MID



"""
    Main parsers
"""
def parse_packet(packet):
    pass

def parse_payload(payload):
    """This function parses only the payload of the advertisment """
    # Get all advs in packet
    advs = []
    org_payload = payload
    while payload:
        lenByte = int(unpack('<B', payload[0])[0])
        if(lenByte > 0):
            adv, payload = payload[:lenByte+1], payload[lenByte+1:]
            advs.append(adv)
        else:
            payload = payload[1:]
            if org_payload:
                print 'Produced 0 length: ', print_bytes(org_payload)
                org_payload = False

    return map(parse_adv, advs)


"""
    Advertisement parsers
"""


def parse_flags(payload, adv):
    bits = format(int(unpack('<B', payload[0])[0]), '#010b')
    #   bit 0 (OFF) LE Limited Discoverable Mode
    adv['LE Limited Discoverable Mode'] = (bits[-1] == '1')

    #   bit 1 (ON) LE General Discoverable Mode
    adv['LE General Discoverable Mode'] = (bits[-2]== '1')

    #   bit 2 (OFF) BR/EDR Not Supported
    adv['BR/EDR Not Supported'] = (bits[-3]== '1')

    #   bit 3 (ON) Simultaneous LE and BR/EDR to Same Device Capable (controller)
    adv['Simultaneous LE and BR/EDR to Same Device Capable (controller)'] = (bits[-4]== '1')

    #   bit 4 (ON) Simultaneous LE and BR/EDR to Same Device Capable (Host)
    adv['Simultaneous LE and BR/EDR to Same Device Capable (Host)'] = (bits[-5]== '1')
    return adv

def parse_mf_data(payload, adv={}):
    b = print_bytes(payload).split(' ')
    adv['mf_id'] = b[1] + b[0]
    if adv['mf_id'] in mf_parsers:
        adv = mf_parsers[adv['mf_id']](payload[2:], adv)

    return adv

def parse_str(payload, adv={}):
    adv['name'] = str(payload)
    return adv

adv_parsers = {0xff: parse_mf_data,
               0x08: parse_str,
               0x09: parse_str,
               0x01: parse_flags
               }

def parse_adv(payload):
    adv = {}
    adv['length'] = int(unpack('<B', payload[0])[0])
    adv['type'] = unpack('<B', payload[1])[0]

    if adv['type'] in adv_parsers:
        adv = adv_parsers[adv['type']](payload[2:], adv)
    return adv

"""
    Manufacturer data parsers
"""


def parse_mf_ibeacon(payload, adv={}):
    adv['byte_0'] =  unpack("<B", payload[0])[0]
    adv['byte_1'] = unpack("<B", payload[1])[0]
    if adv['byte_0'] == 0x02 and adv['byte_1'] == 0x15:
        adv['uuid'] = ''.join(print_bytes(payload[2:18]).split(' ')).lower()
        adv['major'] =  unpack(">H", payload[18:20])[0]
        adv['minor'] = unpack(">H", payload[20:22])[0]

        power = bin(unpack("<B",payload[22])[0])[2:]
        adv['power'] = twos_comp(int(power, 2), len(power))

    return adv

def parse_mf_sensortag(payload, adv={}):
    adv['version'] = unpack("B", payload[0])[0]

    x_axis = unpack("h", payload[3:5])[0] / float(32768 / 2)
    y_axis = unpack("h", payload[5:7])[0] / float(32768 / 2)
    z_axis = unpack("h", payload[7:9])[0] / float(32768 / 2)
    adv['accelerometer'] = {'x':x_axis, 'y': y_axis, 'z': z_axis}

    def __compute_temp(raw_temp):
        SCALE_LSB = 0.03125
        it = raw_temp >> 2

        return float(it) * SCALE_LSB

    raw_die_temp = unpack("H", payload[9:11])[0]
    adv['die_temp'] = __compute_temp(raw_die_temp)

    raw_target_temp = unpack("h", payload[11:])[0]
    adv['target_temp'] = __compute_temp(raw_target_temp)
    return adv


def parse_mf_estimote(payload, adv={}):
    adv['version'] = unpack("B", payload[0])[0]

    adv['uuid'] = "d0d3fa86ca7645ec9bd96af4" + ''.join(x.encode("hex") for x in payload[1:5])
    adv['major'] = unpack(">H", payload[5:7])[0]
    adv['minor']  = unpack(">H", payload[7:9])[0]

    raw_temp = (unpack("<H", payload[11:13])[0] & 0x0fff) << 4

    if (raw_temp & 0x8000) != 0:
        adv['temp'] = ((raw_temp & 0x7fff) - 32768) / 256.0
    else:
        adv['temp']  = raw_temp / 256.0

    adv['is_moving'] = unpack("B", payload[13])[0] & 0x40 != 0

    x_axis = unpack("b", payload[14])[0] * 15.625 / 1000.0
    y_axis = unpack("b", payload[15])[0] * 15.625 / 1000.0
    z_axis = unpack("b", payload[16])[0] * 15.625 / 1000.0

    adv['accelerometer'] = {'x':x_axis, 'y': y_axis, 'z': z_axis}

    def __convert_motion_state(raw):
        unit = (raw >> 6) & 0x03
        duration = raw & 0x3f

        if unit == 1:
            return duration * 60
        elif unit == 2:
            return duration * 3600

        return duration

    motion = unpack("B", payload[17])[0]
    adv['current_motion_state'] = __convert_motion_state(motion)
    motion = unpack("B", payload[18])[0]
    adv['previous_motion_state'] = __convert_motion_state(motion)

    adv['voltage'] = 0

    if unpack("B", payload[13])[0] & 0x80 == 0:
        first_nibble = (unpack("B", payload[13])[0] & 0x3f) << 4
        second_nibble = unpack("B", payload[12])[0] & 0xf
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

    adv['power'] = int(unpack("B", payload[19])[0] & 0x0f)
    adv['channel'] = int(unpack("B", payload[19])[0] >> 4)
#    adv['rssi_1m'] = twos_comp((unpack("B", payload[19])[0] & 0x0f), 2), len
    return adv


mf_parsers = {
           '000D': parse_mf_sensortag,
           '004C': parse_mf_ibeacon,
           '015D': parse_mf_estimote
           }


"""
    Helper functions
"""

def twos_comp(val, bits):
    """compute the 2's compliment of int value val"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val                         # return positive value as is



def print_bytes(payload):
    return ' '.join(['%0.2X' % int(unpack("<B", b)[0]) for b in payload]).strip()
    
