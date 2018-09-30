Blindingly stupid RFID tag reader
=================================

The script here is for use with the II (Interactive Institute) RFID readers.
These are the "little black boxes" of which we have 2 or three lying around
at CWI, leftovers from the Ta2 project.

The boxes consist of an Arduino and an RFID reader, and the Arduino speaks
serial-over-USB at 57600 baud. It simply passes through data from computer
to RFID reader, and in the reverse direction every byte read is encoded in
HEX and transmitted as a single line.

Details about box hardware are not available, open one if you're interested.
Details about the software in the arduino are in ta2/Sandbox/ii/Arduino Stuff/FlashRFID.
Details about the protocol to talk to the RFID reader are in ta2/Sandbox/ii/FamilyGame_02/src/ArduinoComm.
