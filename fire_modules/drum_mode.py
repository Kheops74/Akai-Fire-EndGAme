#   name=AKAI FL Studio Fire - Drum Mode
#   Logique du mode Drum (FPC, Slicex, Omni)

import channels
import device
import screen
import transport
import utils

from fire_modules.mode_base import FireModeBase
from fire_modules.constants import *


class DrumMode(FireModeBase):
    """Gère le mode Drum : FPC, Slicex, Omni channel."""

    def __init__(self, fire_device):
        super().__init__(fire_device)
        self._beatCount = 0
        self._barCount = 0

    # --- Note value calculations ---

    def GetFPCNoteValue(self, Data1):
        # convert to FPC notes
        if Data1 ==52:
            Result = 37 # C#3
        elif Data1 ==53:
            Result = 36 # C3
        elif Data1 ==54:
            Result = 42 # F#3
        elif Data1 ==55:
            Result = 54 # F#4
        elif Data1 ==56:
            Result = 60 # C5
        elif Data1 ==57:
            Result = 61 # C#5
        elif Data1 ==58:
            Result = 62 # D5
        elif Data1 ==59:
            Result = 63 # D#5
        elif Data1 ==36:
            Result = 40 # E3
        elif Data1 ==37:
            Result = 38 # D3
        elif Data1 ==38:
            Result = 46 # A#3
        elif Data1 ==39:
            Result = 44 # G#3
        elif Data1 ==40:
            Result = 64 # E5
        elif Data1 ==41:
            Result = 65 # F5
        elif Data1 ==42:
            Result = 66 # F#5
        elif Data1 ==43:
            Result = 67 # G5
        elif Data1 ==20:
            Result = 48 # C4
        elif Data1 ==21:
            Result = 47 # B3
        elif Data1 ==22:
            Result = 45 # A3
        elif Data1 ==23:
            Result = 43 # G3
        elif Data1 ==24:
            Result = 68 # G#5
        elif Data1 ==25:
            Result = 69 # A5
        elif Data1 ==26:
            Result = 70 # A#5
        elif Data1 ==27:
            Result = 71 # B5
        elif Data1 == 4:
            Result = 49 # C#4
        elif Data1 == 5:
            Result = 55 # G4
        elif Data1 == 6:
            Result = 51 # D#4
        elif Data1 == 7:
            Result = 53 # F4
        elif Data1 == 8:
            Result = 72 # C6
        elif Data1 == 9:
            Result = 73 # C#6
        elif Data1 == 10:
            Result = 74 # D6
        elif Data1 == 11:
            Result = 75 # E6
        else:
            Result = -1
        return Result

    def GetSlicexNoteValue(self, Data1):
        y = Data1 // PadsStride
        x = Data1 - y * PadsStride
        y = PadsH - 1 - y # invert y (we want bottom to top)
        Result = x + y * PadsStride # rebuild note num
        Result  += 5 * 12 # +5 octaves
        return Result

    def GetOmniNoteValue(self, Data1):
        y = Data1 // PadsStride
        x = Data1 - y * PadsStride
        y = PadsH - 1 - y # invert y (we want bottom to top)
        return x + y * PadsStride # rebuild pad num

    # --- Translate note ---

    def TranslateNote(self, event, Data1, Data2):
        """Traduit une note pad en note MIDI pour le mode Drum."""
        if self.fire.CurrentDrumMode in [DrumModeFPC, DrumModeFPCCenter]:
            if (self.fire.CurrentDrumMode == DrumModeFPC):
                Data1 += 4 # offset to match center layout
            Data1 = self.GetFPCNoteValue(Data1)
        elif self.fire.CurrentDrumMode == DrumModeSlicex:
            Data1 = self.GetSlicexNoteValue(Data1)
        elif self.fire.CurrentDrumMode == DrumModeOmni:
            Data1 = self.GetOmniNoteValue(Data1)
        if Data1 < 0:
            return False, Data1, Data2
        return True, Data1, Data2

    # --- Pad event handling ---

    def OnPadEvent(self, event, pad_num):
        """Gère les pads en mode Drum."""
        event.data2 = self.fire.AdaptVelocity(event.data2)
        if (self.fire.CurrentDrumMode == DrumModeFPC) | (self.fire.CurrentDrumMode == DrumModeFPCCenter):
            if (self.fire.CurrentDrumMode == DrumModeFPC):
                event.data1 = pad_num + 4 # offset to match center layout
            else:
                event.data1 = pad_num
            m = self.GetFPCNoteValue(event.data1)
            if m >= 0:
                event.data1 = m
                if event.midiId == MIDI_NOTEON:
                    self.fire.PlayingNotes.append(event.data1)
                else:
                    self.fire.PlayingNotes.remove(event.data1)
                event.handled = False
                return
            else:
                event.handled = True
                return #: nothing
        elif self.fire.CurrentDrumMode == DrumModeSlicex:
            event.data1 = self.GetSlicexNoteValue(pad_num)
            if event.midiId == MIDI_NOTEON:
                self.fire.PlayingNotes.append(event.data1)
            else:
                self.fire.PlayingNotes.remove(event.data1)
            event.handled = False
            return
        elif self.fire.CurrentDrumMode == DrumModeOmni:
            event.data1 = self.GetOmniNoteValue(pad_num)
            if event.midiId == MIDI_NOTEON:
                m = 127
                self.fire.PlayingChannels.append(event.data1)
            else:
                m = -127
                if self.fire.PlayingChannels.count(event.data1) > 0:
                    self.fire.PlayingChannels.remove(event.data1)

            if utils.InterNoSwap(event.data1, 0, channels.channelCount() - 1):
                if not self.fire.AltHeld:
                    channels.midiNoteOn(event.data1, DotNote_Default, m, 0)
                else:
                    self.fire.CutPlayingNotes()
                    channels.selectOneChannel(event.data1)
                    self.fire.DisplayTimedText('Chan: ' + channels.getChannelName(event.data1))

    # --- Jog wheel handling ---

    def OnJogWheel(self, event):
        """Gère le jog wheel en mode Drum."""
        if self.fire.LayoutSelectionMode:
            if event.data2 == 1:
                self.fire.CurrentDrumMode += 1
            else:
                self.fire.CurrentDrumMode -= 1
            if self.fire.CurrentDrumMode > DrumModeLast:
                self.fire.CurrentDrumMode = 0
            elif self.fire.CurrentDrumMode < 0:
                self.fire.CurrentDrumMode = DrumModeLast
            self.fire.CutPlayingNotes()
            self.fire.ClearBtnMap()
            self.Refresh()
            self.fire.DisplayTimedText(DrumModesNamesT[self.fire.CurrentDrumMode])
            return True
        return False

    # --- Refresh ---

    def Refresh(self):
        """Rafraîchit l'affichage des pads en mode Drum."""
        import general

        colors = [0] * 6

        def AddPadDataRGB(x, y, r, g, b):
            if self.fire.BtnMap[x + y * PadsStride] == ((r << 16) + (g << 8) + b):
                return
            dataOut.append(x + y * PadsStride)
            dataOut.append(r)
            dataOut.append(g)
            dataOut.append(b)
            self.fire.BtnMap[x + y * PadsStride] = (r << 16) + (g << 8) + b

        def AddPadDataRGB2(x, y, c):
            if self.fire.BtnMap[x + y * PadsStride] == c:
                return
            dataOut.append(x + y * PadsStride)
            dataOut.append((c & 0x7F0000) >> 16)
            dataOut.append((c & 0x007F00) >> 8)
            dataOut.append((c & 0x7F))
            self.fire.BtnMap[x + y * PadsStride] = c

        # ****

        dataOut = bytearray(0)

        chan = channels.selectedChannel(1)

        if chan >= 0:
            playingNote = self.fire.GetCurStepParam(chan, pPitch)
        else:
            playingNote = -1

        h = 240.0
        s = 0.0
        colors[0] = 0 # unused pad
        v = 0.25
        res, h, s, v = self.fire.ScaleColor(1.0, h, s, v)
        colors[1] = (res & 0xFEFEFE) >> 1 # playing note (from FL)
        v = 1.0
        res, h, s, v = self.fire.ScaleColor(1.0, h, s, v)
        colors[2] = (res & 0xFEFEFE) >> 1 # playing note (by the user)
        h, s, v = utils.RGBToHSVColor(self.fire.KeyColors[self.fire.NoteColorSet][9])
        res, h, s, v = self.fire.ScaleColor(1.0, h, s, v)
        colors[3] = (res & 0xFEFEFE) >> 1 # default drum pad color - bank A
        h, s, v = utils.RGBToHSVColor(self.fire.KeyColors[self.fire.NoteColorSet][10])
        res, h, s, v = self.fire.ScaleColor(1.0, h, s, v)
        colors[4] = (res & 0xFEFEFE) >> 1 # default drum pad color - bank B
        h, s, v = utils.RGBToHSVColor(self.fire.KeyColors[self.fire.NoteColorSet][11])
        res, h, s, v = self.fire.ScaleColor(1.0, h, s, v)
        colors[5] = (res & 0xFEFEFE) >> 1 # default drum pad color - slicex

        if (self.fire.CurrentDrumMode == DrumModeFPC) | (self.fire.CurrentDrumMode == DrumModeFPCCenter):
            if self.fire.CurrentDrumMode == DrumModeFPC:
                n = 4
            else:
                n = 0
            for x in range(0, PadsW):
                for y in range(0, PadsH):                   
                    if (x + n) in range(4, 12):
                        if (playingNote >= 0) & (self.GetFPCNoteValue((x + n) + y * PadsStride) == playingNote):
                            AddPadDataRGB2(x, y, colors[1]) # playing note (from FL)
                        elif self.fire.PlayingNotes.find(self.GetFPCNoteValue((x + n) + y * PadsStride)) >= 0:
                            AddPadDataRGB2(x, y, colors[2]) # playing note (by the user)
                        elif (x + n) < 8:
                            AddPadDataRGB2(x, y, colors[3]) # default pad color - bank A
                        else:
                            AddPadDataRGB2(x, y, colors[4]) # default pad color - bank B
                    else:
                        AddPadDataRGB2(x, y, colors[0]) # unused pad
        elif self.fire.CurrentDrumMode == DrumModeSlicex:
            for x in range(0, PadsW):
                for y in range(0, PadsH):
                    if (playingNote >= 0) & (self.GetSlicexNoteValue(x + y * PadsStride) == playingNote):
                        AddPadDataRGB2(x, y, colors[1]) # playing note (from FL)
                    elif self.fire.PlayingNotes.find(self.GetSlicexNoteValue(x + y * PadsStride)) >= 0:
                        AddPadDataRGB2(x, y, colors[2]) # playing note (by the user)
                    else:
                        AddPadDataRGB2(x, y, colors[5]) # default pad color

        elif self.fire.CurrentDrumMode == DrumModeOmni:  # show a pad per channel
            maxChan = min(channels.channelCount(), 64)
            for n in range(0, maxChan):
                y = n // PadsStride
                x = n - y * PadsStride
                y = PadsH - 1 - y # invert y (we want bottom to top)
                if (general.getVersion() > 8):
                  if(channels.getActivityLevel(n) > 0):
                    AddPadDataRGB2(x, y, colors[1]) # playing note (from FL)
                if n in self.fire.PlayingChannels:
                    AddPadDataRGB2(x, y, colors[2]) # playing note (by the user)
                else:
                    c = channels.getChannelColor(n)
                    h, s, v = utils.RGBToHSVColor(c)
                    c, h, s, v = self.fire.ScaleColor(1.0, h, s, v)
                    r = ((c >> 16) & 0xFF) // 2
                    b = (c & 0xFF) // 2
                    g = ((c >> 8) & 0xFF) // 2
                    AddPadDataRGB(x, y, r, g, b)

            # turn off remaining pads
            if maxChan < 63:
                for n in range(maxChan, 64):
                    y = n // PadsStride
                    x = n - y * PadsStride
                    y = PadsH - 1 - y # invert y (we want bottom to top)
                    AddPadDataRGB2(x, y, colors[0]) # unused pad

        if len(dataOut) > 0:
            screen.unBlank(True)
            self.fire.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)

        self.fire.step_seq_handler.Refresh(True)

    # ==========================
    # Beat Indicators (IDTrackSel1-4)
    # ==========================

    def OnUpdateBeatIndicator(self, value):
        """Update IDTrackSel1-4 LEDs as beat indicators.
        Progressive fill: green for normal bars, red every 4th bar."""
        if not transport.isPlaying():
            self._beatCount = 0
            self._ResetBeatIndicators()
            return

        if value == 1:
            self._beatCount = 1
            self._barCount += 1
        elif value == 2:
            self._beatCount += 1

        if self._beatCount > 4:
            self._beatCount = 0

        is4thBar = (self._barCount % 4) == 0

        for i in range(4):
            if self._beatCount >= i + 1:
                if is4thBar:
                    self.fire.SendCC(IDTrackSel1 + i, SingleColorHalfBright)  # red
                else:
                    self.fire.SendCC(IDTrackSel1 + i, SingleColorFull)  # green
            else:
                self.fire.SendCC(IDTrackSel1 + i, SingleColorOff)

    def _ResetBeatIndicators(self):
        """Turn off all beat indicator LEDs."""
        for i in range(4):
            self.fire.SendCC(IDTrackSel1 + i, SingleColorOff)

    # ==========================
    # Mode lifecycle
    # ==========================

    def OnActivate(self):
        """Called when Drum mode becomes active."""
        self._beatCount = 0
        self._barCount = 0

    def OnDeactivate(self):
        """Called when leaving Drum mode."""
        self._ResetBeatIndicators()
