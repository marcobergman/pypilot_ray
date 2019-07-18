#!/usr/bin/env python

import RPi.GPIO as GPIO
from signalk import kjson
import time
import socket
from datetime import datetime

# ST2000 remote control with Raspberry Pi 2
HOST='127.0.0.1'
PORT=21311

# Tinypilot install:
# /etc/sv/pypilot_lcd/run
# exec nice -n 5 chpst python /mnt/mmcblk0p2/tinypilot/pypilot/ray.py
#

# GPIO constants: connect switches to ground on these GPIO pins
AU = 26      # Auto
M1 = 5       # Minus 1
M10 = 6      # Minus 10
P10 = 12     # Plus 10
P1 = 13      # Plus 1
SB = 21      # Standby
BUZZER = 25  # Buzzer
BLINKER = 19 # Light

MODE_STBY = 1
MODE_AUTO = 2
MODE_TRACK = 4
MODE_GAINS = 5
MODE_P = 6
MODE_I = 7
MODE_D = 8

FACTOR_LOW = 1.1
FACTOR_MEDIUM = 1.5
FACTOR_HIGH = 2.0

# Long press threshold
THRESHOLD = 10

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SB, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Stand By:   1
GPIO.setup(AU, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Auto:       2
GPIO.setup(P1, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # +1:         4
GPIO.setup(P10, GPIO.IN, pull_up_down=GPIO.PUD_UP) # +10:        8
GPIO.setup(M10, GPIO.IN, pull_up_down=GPIO.PUD_UP) # -10:       16
GPIO.setup(M1, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # -1:        32
GPIO.setup(BUZZER, GPIO.OUT)
GPIO.setup(BLINKER, GPIO.OUT)
GPIO.output(BLINKER, 0)


def beep(b):
        if ( b == 1 ):
                GPIO.output(BUZZER, 1)
                time.sleep(0.1)
                GPIO.output(BUZZER, 0)
        if ( b == 2 ):
                GPIO.output(BUZZER, 1)
                time.sleep(0.2)
                GPIO.output(BUZZER, 0)
        if ( b == 3 ):
                beep(1)
                time.sleep(0.1)
                beep(1)


def adjust_gain (mode, factor):
        if (mode == MODE_P):
                gain = "P"
        if (mode == MODE_I):
                gain = "I"
        if (mode == MODE_D):
                gain = "D"
        gain_name = "ap.pilot." + ap_pilot + "." + gain
        gain_name = gain_name.replace("pilot..", "")
        print gain_name
        current_gain = GetSignalkValue (gain_name)
        new_gain = current_gain * factor
        print gain_name + " = " + str(current_gain) + " * " + str(factor) + " = " + str(new_gain)
        SetSignalkValue (gain_name, new_gain)


def adjust_heading (adjustment):
        name = "ap.heading_command"
        current_value = GetSignalkValue(name)
        new_value = current_value + adjustment
        print name + " = " + str(current_value) + " + " + str(adjustment) + " = " + str(new_value)
        SetSignalkValue(name, new_value)


def do_blinker():
        global blinker_counter
        global mode
        if (mode == MODE_STBY):
                light_on = (blinker_counter in [38, 39])
        if (mode == MODE_AUTO):
                light_on = (blinker_counter not in [38, 39])
        if (mode == MODE_TRACK):
                light_on = (blinker_counter not in [1, 2, 5, 6])
        if (mode == MODE_GAINS):
                light_on = (blinker_counter not in [1, 2, 3, 4, 5, 11, 12, 13, 14, 15])
        if (mode in [MODE_P, MODE_I, MODE_D]):
                light_on = (blinker_counter not in [1, 2, 11, 12, 21, 22, 31, 32])
        #print "blinker_counter "+ "{:0>2d}".format(blinker_counter) + " light_on "+str(light_on)
        if (light_on):
                GPIO.output(BLINKER, 1)
        else:
                GPIO.output(BLINKER, 0)
        if (blinker_counter == 0):
                ap_enabled = GetSignalkValue ("ap.enabled")
                if (ap_enabled and ap_mode == 'compass'):
                        mode = MODE_AUTO
                if (ap_enabled and ap_mode == 'gps'):
                        mode = MODE_TRACK
                if (not ap_enabled):
                        mode = MODE_STBY

        blinker_counter = (blinker_counter + 1) % 40


def GetSignalkValue (name):
        connection = socket.create_connection((HOST, PORT))
        request = {'method' : 'get', 'name' : name}
        connection.send(kjson.dumps(request)+'\n')
        line=connection.recv(1024)
        try:
                msg = kjson.loads(line.rstrip())
                value = msg[name]["value"]
        except:
                value = ""
        connection.close();
        return value

def SetSignalkValue (name, value):
        # Write one value to signalk
        connection = socket.create_connection((HOST, PORT))
        request = {'method' : 'set', 'name' : name, 'value' : value}
        connection.send(kjson.dumps(request)+'\n')
        connection.close();


print "Starting up"

print "Connecting to SignalK at " + HOST + ":" + str(PORT)

ap_enabled = GetSignalkValue ("ap.enabled")
ap_mode = GetSignalkValue ("ap.mode")
ap_pilot = GetSignalkValue ("ap.pilot")
print "Autopilot: " + ap_pilot + " / enabled="+ str(ap_enabled) + " / " + ap_mode

mode = MODE_STBY
if (ap_enabled and ap_mode == 'compass'):
        mode = MODE_AUTO
if (ap_enabled and ap_mode == 'gps'):
        mode = MODE_TRACK

beep(3)
print "Ready"

next_mode = mode

blinker_counter = 38

while 1:
        # wait for a button to be pressed
        while (GPIO.input(SB) == 1 and GPIO.input(AU) == 1 and GPIO.input(P1) == 1 and GPIO.input(P10) == 1 and GPIO.input(M10) == 1 and GPIO.input(M1) == 1):
                do_blinker()
                time.sleep (0.05)
        blinker_counter = 0

        # wait for a possible second one or the key to be finished vibrating
        time.sleep (0.05)

        # store the key (or key combination) in one variable
        key = (1-GPIO.input(SB)) + 2*(1-GPIO.input(AU)) + 4*(1-GPIO.input(P1)) + 8*(1-GPIO.input(P10)) + 16*(1-GPIO.input(M10)) + 32*(1-GPIO.input(M1));

        # wait for a long press. Actually, there are no real interesting long presses to implement.
        counter = 0.1
        while (1==2): # (GPIO.input(SB) == 1 and GPIO.input(AU) == 1 and GPIO.input(P1) == 1 and GPIO.input(P10) == 1 and GPIO.input(M10) == 1 and GPIO.input(M1) == 1):
                time.sleep (0.1)
                counter = counter + 1
                if (blinker_counter > THRESHOLD):
                        # Long press
                        counter = -1000;
                        print "Long " + str(key)
                        # Standby
                        if (key == 1):
                                print "Standby (" + str(key) + ")"
                                write_seatalk("02", "FD")
                        beep(2)

        # Short press
        if (counter > 0):

                #print "key = " + str(key)

                # Stand by
                if (key == 1):
                        if (mode in [MODE_AUTO, MODE_P, MODE_I, MODE_D]):
                                print "Stand by"
                                SetSignalkValue ("ap.enabled", False)
                                SetSignalkValue ("servo.command", 0)
                                next_mode = MODE_STBY
                                beep(2)
                        if (mode == MODE_GAINS):
                                next_mode = MODE_D
                                print "Enter D:"
                # Auto
                if (key == 2 and mode != MODE_AUTO):
                        print "Auto"
                        print datetime.now()
                        SetSignalkValue ("ap.heading_command", GetSignalkValue("ap.heading"))
                        SetSignalkValue ("ap.enabled", True)
                        print datetime.now()
                        next_mode = MODE_AUTO
                        if (mode == MODE_TRACK):
                                blinker_counter = 38 # for immediate blinker feedback
                        beep(1)
                # +1
                if (key == 4):
                        if (mode == MODE_AUTO):
                                print "+1"
                                adjust_heading(+1)
                                blinker_counter = 38 # for immediate blinker feedback
                                beep(1)
                        if (mode in [MODE_P, MODE_I, MODE_D]):
                                adjust_gain (mode, FACTOR_LOW)
                        if (mode in [MODE_STBY]):
                                SetSignalkValue ("servo.command", 400)
                                print GetSignalkValue("servo.command")
                                print GetSignalkValue("servo.command")
                                print GetSignalkValue("servo.command")
                                print GetSignalkValue("servo.command")
                                print GetSignalkValue("servo.command")
                                print GetSignalkValue("servo.command")
                                print GetSignalkValue("servo.command")
                # +10
                if (key == 8):
                        if (mode == MODE_AUTO):
                                print "+10"
                                adjust_heading(+10)
                                blinker_counter = 38 # for immediate blinker feedback
                                beep(2)
                        if (mode in [MODE_P, MODE_I, MODE_D]):
                                adjust_gain (mode, FACTOR_MEDIUM)
                # -10
                if (key == 16):
                        if (mode == MODE_AUTO):
                                print "-10"
                                adjust_heading(-10)
                                blinker_counter = 38 # for immediate blinker feedback
                                beep (2)
                        if (mode == MODE_GAINS):
                                next_mode = MODE_I
                                print "Enter I:"
                        if (mode in [MODE_P, MODE_I, MODE_D]):
                                adjust_gain (mode, 1 / FACTOR_MEDIUM)
                # -1
                if (key == 32):
                        if (mode == MODE_AUTO):
                                print "-1"
                                adjust_heading(-1)
                                blinker_counter = 38 # for immediate blinker feedback
                                beep (1)
                        if (mode == MODE_GAINS):
                                next_mode = MODE_P
                                print "Enter P:"
                        if (mode in [MODE_P, MODE_I, MODE_D]):
                                adjust_gain (mode, 1 / FACTOR_LOW)
                # Track -10 & +10
                if (key == 24 and mode != MODE_STBY and mode != MODE_TRACK):
                        print "Track"
                        next_mode = MODE_TRACK
                # Tack Port -1 & -10
                if (key == 48 and mode == MODE_AUTO):
                        print "Tack Port"
                        SetSignalkValue("ap.tack.direction", "port")
                        SetSignalkValue("ap.tack.state", "begin")
                # Tack Starboard +1 & +10
                if (key == 12 and mode == MODE_AUTO):
                        print "Tack Starboard"
                        SetSignalkValue("ap.tack.direction", "starboard")
                        SetSignalkValue("ap.tack.state", "begin")
                # Set gains:  +1 & -1
                if (key == 36 and mode in [MODE_AUTO, MODE_TRACK, MODE_P, MODE_I, MODE_D]):
                        print "Choose gain"
                        next_mode = MODE_GAINS

                mode = next_mode


        # Wait for key to be lifted
        while  (GPIO.input(SB) == 0 or GPIO.input(AU) == 0 or GPIO.input(P1) == 0 or GPIO.input(P10) == 0 or GPIO.input(M10) == 0 or GPIO.input(M1) == 0):
                do_blinker()
                time.sleep (0.1)

