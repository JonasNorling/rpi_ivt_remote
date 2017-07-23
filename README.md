Heatpump remote control for Raspberry Pi
========================================

This little Python script can be used to control a IVT Nordic Inverter
heatpump using an infrared transmitter.

This script is meant to be run on a Rapsberry Pi with an IR
transmitter diode. We talk directly to the LIRC kernel module, so
lirc_rpi must be loaded but lircd must not be running.

Add your user to the video group to get access to /dev/lirc0.

This project was inspired by https://github.com/skarlsso/IRRemoteIVT,
and a description of the IR protocol can be found in that source code.
