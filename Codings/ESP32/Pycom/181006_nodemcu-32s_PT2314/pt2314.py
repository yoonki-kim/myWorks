from pin_map import *
from machine import I2C
from machine import Pin
import time

######################################
#
# Class for controlling PT2314 via i2c
# 4-channel input audo processor
#
# Ronald Diaz ronald@ronalddiaz.net
# MicroPython Potting by Yoonki Kim yoonki.kim71@gmail.com

#i2c = I2C(0, pins=('P10','P11'))     # create and use non-default PIN assignments (P10=SDA, P11=SCL)
#i2c = I2C(0, pins=('GPIO15','GPIO5'))     # create and use non-default PIN assignments (GPIO15=SDA, GPIO2=SCL)
#i2c.init(I2C.MASTER, baudrate=20000) # init as a master

# initialize GPIO12 in GPIO mode and make it an output for TXB0108 OE pin
p12_oe = Pin(GPIO12, mode=Pin.OUT)
p12_oe.value(1)

class PT2314:
    def __init__(self):
        self.i2c = I2C(0, I2C.MASTER, baudrate=100000, pins=(GPIO15, GPIO5))
        self.i2c_address = 0x44
        self.volume = 0x20  # volume = minimum
        self.attenuation_l = 0  # (-x -> x ? )
        self.attenuation_r = 0  # (-x -> x ? )
        self.mute = False  # mute on
        self.loudness = True  # loudness on
        self.channel = 0  # channel 0 selected [ 0 -> 3 ]
        self.loudnessGain = 0x00  # Loudness Gain [0dB ~ +11.25dB, 3.75dB step]
        self.bass = 0x0F  # bass = 0
        self.treble = 0x0F  # treble = 0
        self._updateAll()  # Initialise all

        # Tone lookup values
        self.tone_values = [(-14, 0x00), (-12, 0x01), (-10, 0x02), (-8, 0x03), (-6, 0x04), (-4, 0x05), (-2, 0x06),
                            (0, 0x07), (2, 0x0E), (4, 0x0D), (6, 0x0C), (8, 0x0B), (10, 0x0A), (12, 0x09), (14, 0x08)]

    # High Level Commands

    def powerOff(self):
        self.mute = True
        self._updateAttenuation()

    def volume_to_pt2314(self, vol):
        int_vol = int(63 - ((vol * 63) / 100))
        return int_vol

    def setVolume(self, vol):    # 0~100%
        self.volume = self.volume_to_pt2314(vol)
        self._updateVolume()

    def attenuation_to_pt2314(self, atten):
        int_atten = int(31 - ((atten * 31) / 100))
        return int_atten

    def setAttenuation(self, left, right):    # 0~100%
        self.attenuation_l = self.attenuation_to_pt2314(left)
        self.attenuation_r = self.attenuation_to_pt2314(right)
        self._updateAttenuation()

    def muteOn(self):
        self.mute = True
        self._updateAttenuation()

    def muteOff(self):
        self.mute = False
        self._updateAttenuation()

    def selectChannel(self, ch):
        self.channel = ch
        self._updateAudioSwitch()

    def loudnessOn(self):
        self.loudness = True
        self._updateAudioSwitch()

    def loudnessOff(self):
        self.loudness = False
        self._updateAudioSwitch()

    def setGain(self, sel):    # gain = [0dB, 3.75dB, 7.5dB, 11.25dB]
        gain = [0x18, 0x10, 0x08, 0x00]
        self.loudnessGain = gain[sel]
        self._updateAudioSwitch()

    def setBass(self, bass):
        self.bass = self._lookupTone(int(bass))
        self._updateBass()
        return self._lookupToneReverse(self.bass)

    def setTreble(self, treble):
        self.treble = self._lookupTone(int(treble))
        self._updateTreble()
        return self._lookupToneReverse(self.treble)

    # Low Level Commands

    def _updateVolume(self):
        self._sendByte(self.volume)

    def _updateAttenuation(self):
        if self.mute == True:
            self._sendByte(0xDF)
            self._sendByte(0xFF)
        else:
            self._sendByte(0xC0 | self.attenuation_l)
            self._sendByte(0xE0 | self.attenuation_r)

    def _updateAudioSwitch(self):
        audioByte = 0x40
        audioByte |= self.loudnessGain
        if self.loudness == True:  # Loudness On
            audioByte |= 0x00
        else:
            audioByte |= 0x04
        audioByte |= self.channel  # Select Channel
        self._sendByte(audioByte)  # Send Bytemo

    def _updateBass(self):
        self._sendByte(0x60 | self.bass)

    def _updateTreble(self):
        self._sendByte(0x70 | self.treble)

    def _lookupTone(self, value):
        try:
            return next(x for x in self.tone_values if x[0] == value)[1]
        except StopIteration:
            return 0x0F

    def _lookupToneReverse(self, value):
        try:
            return next(x for x in self.tone_values if x[1] == value)[0]
        except StopIteration:
            return 0

    def _updateAll(self):
        self._updateVolume()
        self._updateAttenuation()
        self._updateAudioSwitch()
        self._updateBass()
        self._updateTreble()

    def _sendByte(self, b):
        print("data: %x" % b)
        try:
            self.i2c.writeto(self.i2c_address, bytes([b]))  # send data via i2c
        except Exception as e:
            print("Error : ", e)
