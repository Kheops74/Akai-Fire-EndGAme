#   name=AKAI FL Studio Fire - Utility classes
#   Classes utilitaires extraites de device_Fire.py

class TAccentModeParams:
    def __init__(self, pitch, vel, pan, modx, mody):
        self.Pitch = pitch
        self.Vel = vel
        self.Pan = pan
        self.ModX = modx
        self.ModY = mody

class TiniKeyRecord:
    def __init__(self, name, prt):
        self.Name = name
        self.prt = prt

class TiniKeySection:
    def __init__(self, name, keys):
        self.Name = name
        self.keys = keys

class TMidiEvent:
    def __init__(self):
        self.handled = False
        self.timestamp = 0
        self.status = 0
        self.data1 = 0
        self.data2 = 0
        self.port = 0
        self.isIncrement = 0
        self.res = 0.0
        self.inEV = 0
        self.outEV = 0
        self.midiId = 0
        self.midiChan = 0
        self.midiChanEx = 0
        self.SenderId = 0
        self.pmeFlags = 0
        self.sysexLen = 0
        self.sysexData = 0
