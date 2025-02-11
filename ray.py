#!/usr/bin/env python
#
#   2019 Marco Bergman
#
# This Program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.

import sys, os, time, math
import RPi.GPIO as GPIO

from datetime import datetime
from pypilot.client import pypilotClient
from pypilot import pyjson
from values import *

# GPIO constants: connect switches to ground on these GPIO pins
AU = 26      # Auto
M1 = 5       # Minus 1
M10 = 6      # Minus 10
P10 = 12     # Plus 10
P1 = 13      # Plus 1
SB = 21      # Standby
BUZZER = 20  # Buzzer
BLINKER = 19 # Light

FACTOR_LOW = 1.1
FACTOR_MEDIUM = 1.5
FACTOR_HIGH = 2.0
SLOW = 0.2
FAST = 2.0
THRESHOLD = 6 # Long press threshold in 0.1 sec
TACK_ANGLE = 110 # Degrees

MODE_STBY, MODE_AUTO, MODE_TRACK, MODE_GAINS, MODE_P, MODE_I, MODE_D, MODE_WAYPOINT_R, MODE_WAYPOINT_L, MODE_WIND = range(10)


class RayClient():
    def __init__(self):
        self.client = False
        self.remote_key = 0
        self.blinker_counter = 0
        self.mode = MODE_STBY
        self.last_servo_command = 0
        self.last_bell = datetime.now()

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


    def connect(self):

        watchlist = ['ap.enabled', 'ap.mode', 'ap.pilot', 'ap.bell_server', 'ap.heading', 'ap.heading_command',
                     'gps.source', 'wind.source', 'servo.controller', 'servo.flags',
                     'ap.pilot.basic.P', 'ap.pilot.basic.I', 'ap.pilot.basic.D']

        self.last_msg = {}
        self.last_msg['ap.bell_server'] = "10.10.10.4"

        host = ''
        if len(sys.argv) > 1:
            host = sys.argv[1]

        try:
            self.client = pypilotClient(host)

            for name in watchlist:
                self.client.watch(name)

            print('connected')
        except Exception as e:
            print(e)
            self.client = False
            time.sleep(1)



    def last_val(self, name):
        if name in self.last_msg:
            return self.last_msg[name]
        return 'N/A'



    def set(self, name, value):
        if self.client:
            # print ("setting {} to {}".format(name, value))
            self.client.set(name, value)



    def bell(self, b):

        bell_server = self.last_val('ap.bell_server')
        #print ("bell_server=" + str(bell_server))

        if (bell_server != 'N/A'):
            if ( b == 1 ):
                    file = '1bells.wav'
            if ( b == 2 ):
                    file = '2bells.wav'
            try:
                    os.system('echo ' + file + ' | nc -w 1 ' + bell_server + ' 7000')
            except Exception as e:
                    print('ex', e)
            self.last_bell = datetime.now()



    def beep(self, b):
        if ( b == 1 ):
                GPIO.output(BUZZER, 1)
                time.sleep(0.05)
                GPIO.output(BUZZER, 0)
        if ( b == 2 ):
                GPIO.output(BUZZER, 1)
                time.sleep(0.1)
                GPIO.output(BUZZER, 0)
        if ( b == 3 ):
                self.beep(1)
                time.sleep(0.05)
                self.beep(1)
        if ( b == 4 ):
                self.beep(3)
                time.sleep(0.05)
                self.beep(3)



    def adjust_gain (self, mode, factor):
        if (mode == MODE_P):
                gain = "P"
        if (mode == MODE_I):
                gain = "I"
        if (mode == MODE_D):
                gain = "D"
        gain_name = "ap.pilot." + self.last_val("ap.pilot") + "." + gain
        gain_name = gain_name.replace("pilot..", "")
        current_gain = self.last_val (gain_name)
        new_gain = current_gain * factor
        print (gain_name + " = " + str(current_gain) + " * " + str(factor) + " = " + str(new_gain))
        self.set (gain_name, new_gain)



    def adjust_heading (self, mode, adjustment):
        name = "ap.heading_command"
        current_value = self.last_val (name)
        if current_value == "N/A":
                current_value = 0
        if (mode != MODE_WIND):
                new_value = current_value + adjustment
        else:
                new_value = current_value - adjustment
        print (name + " = " + str(current_value) + " + " + str(adjustment) + " = " + str(new_value))
        self.set (name, new_value)



    def doBlinker(self):
        if (self.blinker_counter != 1000):
                ap_enabled = self.last_val ("ap.enabled")
                ap_mode = self.last_val ("ap.mode")
                if (ap_enabled and ap_mode == 'compass' and self.mode not in [MODE_P, MODE_I, MODE_D, MODE_GAINS, MODE_WAYPOINT_L, MODE_WAYPOINT_R]):
                        self.mode = MODE_AUTO
                if (ap_enabled and ap_mode == 'gps' and self.mode not in [MODE_P, MODE_I, MODE_D, MODE_GAINS, MODE_WAYPOINT_L, MODE_WAYPOINT_R]):
                        self.mode = MODE_TRACK
                if (ap_enabled and ap_mode == 'wind' and self.mode not in [MODE_P, MODE_I, MODE_D, MODE_GAINS, MODE_WAYPOINT_L, MODE_WAYPOINT_R]):
                        self.mode = MODE_WIND
                if (not ap_enabled):
                        self.mode = MODE_STBY

        if (self.mode == MODE_STBY):
                light_on = (self.blinker_counter in [1, 2])
        if (self.mode == MODE_AUTO):
                light_on = (self.blinker_counter not in [1, 2])
        if (self.mode == MODE_TRACK):
                light_on = (self.blinker_counter not in [1, 2, 5, 6])
        if (self.mode == MODE_WIND):
                light_on = (self.blinker_counter not in [1, 2, 5, 6, 9, 10])
        if (self.mode == MODE_GAINS):
                light_on = (self.blinker_counter % 6 > 3)
        if (self.mode in [MODE_P, MODE_I, MODE_D]):
                light_on = (self.blinker_counter not in [1, 2, 11, 12, 21, 22, 31, 32])
        if (self.mode in [MODE_WAYPOINT_L, MODE_WAYPOINT_R]):
                light_on = (self.blinker_counter % 10 > 5)
                if ((datetime.now() - self.last_bell).total_seconds() > 5):
                        if self.mode in [MODE_WAYPOINT_R]:
                                self.bell(1)
                                self.beep(3)
                        else:
                                self.bell(2)
                                self.beep(4)
        if (light_on):
                GPIO.output(BLINKER, 1)
        else:
                GPIO.output(BLINKER, 0)

        self.blinker_counter = (self.blinker_counter + 1) % 40



    def getMessages(self):
        # Listen out for SignalK messages; if they arrive, update them in self.last_msg dictionary
        while True:
            result = False
            if not self.client:
                print("reconnecting...")
                self.connect()
                print("reconnected...")
                break
            try:
                msgs = self.client.receive()
            except Exception as e:
                print('disconnected', e)
                self.client = False

            if not msgs:
                break

            for name, value in msgs.items():
                self.last_msg[name] = value
                #print(str(name) + " = " + str(value))



    def handleKey(self, key):
        print("key = " + str(key) +  ", mode = " + str(self.mode))
        next_mode = self.mode

        # Standby key
        if (key == 1):
                if (self.mode in [MODE_STBY, MODE_AUTO, MODE_WIND, MODE_P, MODE_I, MODE_D, MODE_TRACK, MODE_WAYPOINT_L, MODE_WAYPOINT_R]):
                        print ("Stand by")
                        self.set ("ap.enabled", False)
                        self.set ("servo.command", 0)
                        self.set ("imu.compass.calibration.locked", True)
                        next_mode = MODE_STBY
                        self.beep(2)
                if (self.mode == MODE_GAINS):
                        next_mode = MODE_D
                        print ("Enter D:")

        # Auto key
        if (key == 2 and self.mode != MODE_AUTO):
                self.beep(1)
                print ("Auto")
                self.set ("ap.heading_command", int(self.last_val("ap.heading")))
                self.set ("ap.enabled", True)
                self.set ("ap.mode", "compass")
                self.set ("imu.compass.calibration.locked", False)
                next_mode = MODE_AUTO

        # +1
        if (key == 4):
                self.beep(1)
                if (self.mode in [MODE_AUTO, MODE_TRACK, MODE_WIND]):
                        print ("+1")
                        self.adjust_heading(self.mode, +1)
                if (self.mode in [MODE_P, MODE_I, MODE_D]):
                        self.adjust_gain (self.mode, FACTOR_LOW)
                if (self.mode in [MODE_STBY]):
                        servo_command = -SLOW
                        self.set ("servo.command", servo_command)
                        self.last_servo_command = servo_command
        # -1
        if (key == 32):
                self.beep (1)
                if (self.mode in [MODE_AUTO, MODE_TRACK, MODE_WIND]):
                        print ("-1")
                        self.adjust_heading(self.mode, -1)
                if (self.mode == MODE_GAINS):
                        next_mode = MODE_P
                        print ("Enter P:")
                if (self.mode in [MODE_P, MODE_I, MODE_D]):
                        self.adjust_gain (self.mode, 1 / FACTOR_LOW)
                if (self.mode in [MODE_STBY]):
                        servo_command = +SLOW
                        self.set ("servo.command", servo_command)
                        self.last_servo_command = servo_command
        # +10
        if (key == 8):
                self.beep(2)
                if (self.mode in [MODE_AUTO, MODE_TRACK, MODE_WIND]):
                        print ("+10")
                        self.adjust_heading(self.mode, +10)
                if (self.mode in [MODE_P, MODE_I, MODE_D]):
                        self.adjust_gain (self.mode, FACTOR_MEDIUM)
                if (self.mode in [MODE_STBY]):
                        servo_command = -FAST
                        self.set ("servo.command", servo_command)
                        self.last_servo_command = servo_command
        # -10
        if (key == 16):
                self.beep (2)
                if (self.mode in [MODE_AUTO, MODE_TRACK, MODE_WIND]):
                        print ("-10")
                        self.adjust_heading(self.mode, -10)
                if (self.mode == MODE_GAINS):
                        next_mode = MODE_I
                        print ("Enter I:")
                if (self.mode in [MODE_P, MODE_I, MODE_D]):
                        self.adjust_gain (self.mode, 1 / FACTOR_MEDIUM)
                if (self.mode in [MODE_STBY]):
                        servo_command = +FAST
                        self.set ("servo.command", servo_command)
                        self.last_servo_command = servo_command
        # Track -10 & +10
        if (key == 24 and self.mode in [MODE_AUTO, MODE_WAYPOINT_L, MODE_WAYPOINT_R]):
                self.beep (3)
                print ("Track")
                self.set ("ap.enabled", True)
                self.set ("ap.mode", "gps")
                next_mode = MODE_TRACK
        # Wind Stby & Auto
        if (key == 3 and self.mode in [MODE_AUTO, MODE_TRACK]):
                self.beep (4)
                print ("Wind")
                self.set ("ap.enabled", True)
                self.set ("ap.mode", "wind")
                next_mode = MODE_WIND
        # Tack Port -1 & -10
        if (key == 48 and self.mode == MODE_AUTO):
                self.beep (3)
                print ("Tack Port")
                self.adjust_heading(self.mode, -TACK_ANGLE)
        # Tack Starboard +1 & +10
        if (key == 12 and self.mode == MODE_AUTO):
                self.beep (3)
                print ("Tack Starboard")
                self.adjust_heading(self.mode, +TACK_ANGLE)
        # Set gains:  +1 & -1
        if (key == 36 and self.mode in [MODE_AUTO, MODE_TRACK, MODE_P, MODE_I, MODE_D]):
                self.beep (3)
                print ("Choose gain")
                next_mode = MODE_GAINS
        if (key == 33 and self.mode in [MODE_STBY]):
                print ("Calibrate on in standby")
                self.beep(4)
                self.set ("imu.compass.calibration.locked", False)
        # Artificial mode: Waypoint Arrival
        if (key == 1000 and self.mode in [MODE_TRACK]):
                print ("Waypoint arrival, confirm with 'Track'")
                next_mode = MODE_WAYPOINT_R
                self.bell(1)
        if (key == 1001 and self.mode in [MODE_TRACK]):
                print ("Waypoint arrival, confirm with 'Track'")
                next_mode = MODE_WAYPOINT_L
                self.bell(2)
        if (key == 1003 and self.mode in [MODE_WAYPOINT_R, MODE_WAYPOINT_L]):
                print ("Waypoint remote cancel")
                next_mode = MODE_TRACK
        # Steer into Wind:
        if (key == 1004):
                self.beep (4)
                print ("Steer into Wind")
                self.set ("ap.enabled", True)
                self.set ("ap.mode", "wind")
                self.getMessages()
                time.sleep (0.05)
                self.set ("ap.heading_command", 0)
                next_mode = MODE_WIND

        if self.mode != next_mode:
                blinker_counter = 1;
                self.mode = next_mode
        self.remote_key = 0




    def processKeys(self):
        # wait for a button to be pressed. In the meantime, listen for SignalK messages and blink the LED:
        while (GPIO.input(SB) == 1 and GPIO.input(AU) == 1 and GPIO.input(P1) == 1 and GPIO.input(P10) == 1 and GPIO.input(M10) == 1 and GPIO.input(M1) == 1 and self.remote_key == 0):
                self.getMessages()
                self.doBlinker()
                time.sleep (0.05)
                try:
                        with open('/tmp/remote', 'r') as myfile:
                                line = myfile.read().replace("\n", "")
                        print ("remote=" + line)
                        os.remove('/tmp/remote')
                        self.remote_key = int(line)
                except:
                        self.remote_key = 0


        # wait for a possible second button to be pressed in parallel, or at least for the button to be finished vibrating
        time.sleep (0.05)

        # store the key (or key combination) in one variable
        key = (1-GPIO.input(SB)) + 2*(1-GPIO.input(AU)) + 4*(1-GPIO.input(P1)) + 8*(1-GPIO.input(P10)) + 16*(1-GPIO.input(M10)) + 32*(1-GPIO.input(M1)) + self.remote_key;

        # wait for a long press.
        counter = 0
        while (GPIO.input(SB) == 0 or GPIO.input(AU) == 0 or GPIO.input(P1) == 0 or GPIO.input(P10) == 0 or GPIO.input(M10) == 0 or GPIO.input(M1) == 0) and counter < 1000 and key == 3:
                time.sleep (0.1)
                counter = counter + 1
                if (counter > THRESHOLD):
                        # Wind
                        if (key == 3):
                                key = 1004
                                counter = 1000;
                                self.beep(2)

        self.handleKey(key)

        # Wait for key to be lifted
        while  (GPIO.input(SB) == 0 or GPIO.input(AU) == 0 or GPIO.input(P1) == 0 or GPIO.input(P10) == 0 or GPIO.input(M10) == 0 or GPIO.input(M1) == 0):
                self.doBlinker()
                time.sleep (0.05)
                if key in [4,8,16,32] and self.mode in [MODE_STBY]:
                        self.set ("servo.command", self.last_servo_command)
                        self.getMessages() # This line has to be here to 'flush' servo.command messages to the server.

        # Key released
        # Immediately stop manual movement:
        if (self.mode in [MODE_STBY]):
                self.set ("servo.command", 0)



def main():
    print('init...')

    rayclient = RayClient()
    rayclient.connect()

    rayclient.bell(2)
    rayclient.beep(1)

    while True:
        rayclient.processKeys()

if __name__ == '__main__':
    main()
