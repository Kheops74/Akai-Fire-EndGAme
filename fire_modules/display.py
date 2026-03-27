#   name=AKAI FL Studio Fire - Display Management
#   Logique de l'affichage OLED et écran

import screen
import utils
import device
import mixer
import general
import time

from fire_modules.constants import *


class DisplayManager:
    """Gère l'affichage OLED du Akai Fire : texte, barres, meters, screen modes."""

    def __init__(self, fire_device):
        self.fire = fire_device

    def InitScreen(self):
        """Initialise l'écran OLED."""
        screen.init(self.fire.DisplayWidth, self.fire.DisplayHeight, TextRowHeight, FireFontSize, 0xFFFFFF, 0)
        sysexHeader = int.from_bytes(bytes([MIDI_BEGINSYSEX, ManufacturerIDConst, DeviceIDBroadCastConst, ProductIDConst, MsgIDSendPackedOLEDData]), byteorder='little')
        screen.setup(sysexHeader, ScreenActiveTimeout, ScreenAutoTimeout, TextScrollPause, TextScrollSpeed, TextDisplayTime)
        self.fire.BgCol = 0x000000
        self.fire.FgCol = 0xFFFFFF
        self.fire.DiCol = 0xFFFFFF
        screen.fillRect(0, 0, self.fire.DisplayWidth, self.fire.DisplayHeight, 0)

    def DeInitScreen(self):
        """Dé-initialise l'écran OLED."""
        screen.deInit()

    def DisplayText(self, Font, Justification, PageTop, Text, CheckIfSame, DisplayTime=0):
        screen.displayText(Font, Justification, PageTop, Text, CheckIfSame, DisplayTime)

    def DisplayBar(self, Text, Value, Bipolar):
        screen.displayBar(0, TextRowHeight * TimedTextRow, Text, Value, Bipolar)

    def DisplayTimedText(self, Text):
        screen.displayTimedText(Text, TimedTextRow)

    def ClearDisplayText(self):
        dataOut = bytearray(3)
        dataOut[0] = 0
        dataOut[1] = 0
        for n in range(0, 8):
            dataOut[2] = n
            self.fire.SendMessageToDevice(MsgIDDrawScreenText, len(dataOut), dataOut)

    def ClearDisplay(self):
        screen.fillRect(0, 0, self.fire.DisplayWidth, self.fire.DisplayHeight, self.fire.BgCol)
        screen.update()

    def SetScreenMode(self, mode):
        if self.fire.ScreenMode != mode:
            self.fire.ScreenMode = mode
            i = screen.findTextLine(0, 20, 128, 20 + 44)
            if (general.getVersion() > 8):
                if (i >= 0):
                    screen.removeTextLine(i, 1)
                if mode in [ScreenModePeak, ScreenModeScope]:
                    screen.addMeter(mode, 0, 20, 128, 20 + 44)

    def UpdateScreenIdle(self):
        """Gère la mise à jour de l'écran pendant l'idle (FPS, blanking, animation)."""
        res = screen.findTextLine(0, 20, 128, 20 + 44)
        if (res < 0) & (self.fire.ScreenMode != ScreenModeNone):
            i = self.fire.ScreenMode
            self.fire.ScreenMode = ScreenModeNone
            self.SetScreenMode(i)

        screen.animateText(self.fire.ScreenMode)
        t = time.time()

        if self.fire.LastIdleSec == 0:
            self.fire.LastIdleSec = t
            self.fire.IdleFPS = 0
        else:
            if t < self.fire.LastIdleSec:
                i = int((int(t) + 0x100000000) - int(self.fire.LastIdleSec))
            else:
                i = (t - self.fire.LastIdleSec)
            if i >= 1000:
                screenActiveCounter = screen.getScreenActiveCounter()
                if (screenActiveCounter > 0) & (not screen.isBlanked()):
                    screenActiveCounter -= 1
                    screen.setScreenActiveCounter(screenActiveCounter)
                    if screenActiveCounter > ScreenAutoTimeout:
                        screen.keepDisplayActive()
                    elif screenActiveCounter == 0:
                        screen.blank(True, self.fire.ScreenMode)

                self.fire.LastIdleSec = t
                R = utils.TRect(0, TextRowHeight * FPSRow, self.fire.DisplayWidth, (TextRowHeight * FPSRow) + TextRowHeight)
                R2 = R
                utils.OffsetRect(R2, 0, TextOffset)
                screen.eraseRect(R2.Left, R2.Top, R2.Right, R2.Bottom)
                screen.drawText(0, 'FPS: ' + str(self.fire.IdleFPS), R2.Left, R2.Top, R2.Right, R2.Bottom)
                self.fire.IdleFPS = 0
            else:
                self.fire.IdleFPS += 1

        if screen.isUnBlank():
            screen.blank(False, self.fire.ScreenMode)

        screen.update()
        screen.unBlank(False)
