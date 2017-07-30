#!/usr/bin/python
#
# Control IVT Nordic Inverter heat pump over the IR interface.
# This script is meant to be run on a Rapsberry Pi with an IR transmitter diode.
# We talk directly to the LIRC kernel module, so lirc_rpi must be loaded but
# lircd must not be running.
#
# Add your user to the video group to get access to /dev/lirc0.
#
# Note: The code reverses the order of numeric fields, which makes me strongly
# believe that the data actually is sent LSB first.
#
# Some of this code is derived from https://github.com/skarlsso/IRRemoteIVT
# (license unclear)

import argparse
import logging
import struct

def reverse(n, bits):
    o = 0
    for i in range(0, bits):
        o |= ((n >> i) & 1) << (bits - i - 1)
    return o

def encode_temperature(in_t):
    if in_t == 10:
        in_t = 17 # Special case
    elif in_t < 18 or in_t > 32:
        raise ValueError("Bad temperature")
    t = in_t - 17
    return reverse(t, 4)

def calculate_parity(message):
    parity = 0
    for byte in message:
        parity ^= byte
    return (parity & 0x0f) ^ parity >> 4

# Encode data bytes to a pulse train
# The IR protocol is based on T = 450 us time quanta.
#  - the message starts with a preamble of 8 high, 4 low, 1 high.
#  - a 0 bit is encoded as 1 low T followed by 1 high T,
#  - a 1 bit is encoded as 3 low T followed by 1 high T,
def encode(message):
    T = 450
    pulses = [ 8*T, 4*T, 1*T ]
    for byte in message:
        for bit in range(0, 8):
            if byte & (0x80 >> bit):
                pulses += [ 3*T, 1*T ]
            else:
                pulses += [ 1*T, 1*T ]
    return pulses

# Hand off the message to the LIRC kernel module
def send_message(message):
    log = logging.getLogger("rpi_ivt_remote")
    log.debug("Sending %s" % ["%02x" % n for n in message])
    pulses = encode(message)
    with open("/dev/lirc0", "w") as lirc:
        encoded = struct.pack("=%di" % len(pulses), *pulses)
        lirc.write(encoded)

# Encode and send a command
def send_command(on=False, temp=20, fan=2, ion=False):
    message = [
        0x55, # preamble/sync
        0x5a, # preamble/sync
        0xf3, # preamble/sync
        0x08, # preamble/sync
        0xc0, # temperature
        0x84, # state
        0x84, # mode, fan strength
        0x18, # time hours
        0x10, # rotate
        0x01,
        0x00, # time minutes
        0x0f, # ion mode
        0x80, # CRC
        ]

    message[4] = encode_temperature(temp) << 4
    if on:
        message[5] = 0x88
    else:
        message[5] = 0x84
    message[6] = 0x80 | (fan << 1)
    if ion:
        message[11] = 0x2f
    message[12] = 0x80 | calculate_parity(message)

    send_message(message)    

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    description = "Control IVT Nordic Inverter heat pump over the IR interface"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("-t", metavar="TEMP", type=int, help="Set temperature")
    parser.add_argument("--off", help="Turn off", action="store_true")
    parser.add_argument("--on", help="Turn on", action="store_true")
    parser.add_argument("--autofan", help="Set fan to auto power", action="store_true")
    parser.add_argument("--fan", help="Fan speed (1,2,3)", type=int)
    parser.add_argument("--ion", help="Engage ion thrusters", action="store_true")

    args = parser.parse_args()
    
    if args.off:
        on = False
    elif args.on:
        on = True
    else:
        parser.error("Not on nor off")

    temp = 18
    ion = False
    fan_value = 0x2

    if args.on:
        if args.t is None:
            parser.error("Missing temperature")
        temp = args.t
        if args.autofan:
            fan_value = 0x2
        elif args.fan == 1:
            fan_value = 0x6
        elif args.fan == 2:
            fan_value = 0x5
        elif args.fan == 3:
            fan_value = 0x7
        else:
            parser.error("Missing fan speed")

    send_command(on=on, temp=temp, fan=fan_value, ion=args.ion)
