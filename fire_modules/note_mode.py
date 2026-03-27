#   name=AKAI FL Studio Fire - Note Mode
#   Piano chromatique : 4 rangées = 4 octaves, 12 notes/rangée, mode accords

import channels
import device
import screen
import transport
import utils

from fire_modules.mode_base import FireModeBase
from fire_modules.constants import *

# Layout: 4 rows x 16 cols
# Cols 0-11: 12 chromatic notes (C C# D D# E F F# G G# A A# B)
# Cols 12-15: function pads
NM_CHROMATIC = 12

# Black key semitone indices within octave
NM_BLACK_KEYS = {1, 3, 6, 8, 10}  # C#, D#, F#, G#, A#

# Note names
NM_NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Colors (Step Edit style)
NM_COL_OFF       = 0x000000
NM_COL_WHITE     = 0x1A1A1A      # dim white for white keys
NM_COL_BLACK     = 0x180030      # dim violet for black keys
NM_COL_ROOT      = 0x002080      # blue tint for root note (C)
NM_COL_PLAYING   = 0x00FF00      # green when note is held/playing
NM_COL_CHORD_ON  = 0xFF4400      # orange indicator for chord mode pad
NM_COL_CHORD_OFF = 0x221100      # dim orange when chord mode is off
NM_COL_FUNC      = 0x060606      # very dim for unused function pads


class NoteMode(FireModeBase):
    """Mode Piano chromatique : 4 octaves sur 4 rangées, 12 notes par rangée, mode accords."""

    def __init__(self, fire_device):
        super().__init__(fire_device)
        self.ChordMode = False
        self._heldNotes = {}  # pad_num -> list of MIDI notes currently held for that pad
        self._beatCount = 0   # beat counter for IDTrackSel1-4 indicators
        self._barCount = 0       # bar counter for 4-bar red cycle

    # ==========================
    # Note mapping
    # ==========================

    def GetNoteForPad(self, pad_num):
        """Get MIDI note number for a pad. Returns -1 if function pad or out of range."""
        col = pad_num % PadsStride
        if col >= NM_CHROMATIC:
            return -1
        row = pad_num // PadsStride
        # Bottom row (row 3 in data) = lowest octave, top row (row 0) = highest
        octave = PadsH - 1 - row
        note = self.fire.KeyOffset + (octave * 12) + col
        return note if 0 <= note <= 127 else -1

    def GetNoteModeName(self):
        """Get display name for OLED."""
        if self.ChordMode:
            chordName = self.fire.chord_select_handler.GetCurrentChordName()
            return 'Piano CHORD: ' + chordName
        return 'Piano'

    def GetOctaveRangeText(self):
        """Get the octave range text for OLED."""
        lowNote = self.fire.KeyOffset
        highNote = self.fire.KeyOffset + (PadsH * 12) - 1
        highNote = min(highNote, 127)
        lowName = NM_NOTE_NAMES[lowNote % 12] + str((lowNote // 12) - 2)
        highName = NM_NOTE_NAMES[highNote % 12] + str((highNote // 12) - 2)
        return lowName + ' - ' + highName

    # ==========================
    # Pad Events
    # ==========================

    def OnPadEvent(self, event, pad_num):
        """Handle pad press/release in piano mode."""
        chan = channels.channelNumber(True)
        if chan < 0:
            self.fire.PlayingNotes = bytearray(0)
            event.handled = True
            return

        col = pad_num % PadsStride
        if col >= NM_CHROMATIC:
            # Function pads (cols 12-15): no action
            event.handled = True
            return

        note = self.GetNoteForPad(pad_num)
        if note < 0:
            event.handled = True
            return

        velocity = self.fire.AdaptVelocity(event.data2)

        if event.midiId == MIDI_NOTEON:
            if self.ChordMode:
                intervals = self.fire.chord_select_handler.GetCurrentChordIntervals()
                notes = []
                for iv in intervals:
                    n = note + iv
                    if 0 <= n <= 127:
                        notes.append(n)
                self._heldNotes[pad_num] = notes
                # Play all chord notes via channels.midiNoteOn
                try:
                    for n in notes:
                        channels.midiNoteOn(chan, n, velocity)
                        if n not in self.fire.PlayingNotes:
                            self.fire.PlayingNotes.append(n)
                    event.handled = True
                except Exception:
                    # Fallback: play root note via passthrough
                    event.data1 = note
                    event.data2 = velocity
                    if note not in self.fire.PlayingNotes:
                        self.fire.PlayingNotes.append(note)
                    event.handled = False
                # OLED: show root note of chord
                self._DisplayNoteOLED(note)
            else:
                # Single note — passthrough to FL Studio
                self._heldNotes[pad_num] = [note]
                event.data1 = note
                event.data2 = velocity
                if note not in self.fire.PlayingNotes:
                    self.fire.PlayingNotes.append(note)
                event.handled = False
                # OLED: show note
                self._DisplayNoteOLED(note)
        else:
            # Note off
            notes = self._heldNotes.pop(pad_num, [note])
            if self.ChordMode and len(notes) > 1:
                try:
                    for n in notes:
                        channels.midiNoteOn(chan, n, 0)
                        if n in self.fire.PlayingNotes:
                            self.fire.PlayingNotes.remove(n)
                    event.handled = True
                except Exception:
                    event.data1 = notes[0] if notes else note
                    event.data2 = 0
                    if event.data1 in self.fire.PlayingNotes:
                        self.fire.PlayingNotes.remove(event.data1)
                    event.handled = False
            else:
                n = notes[0] if notes else note
                event.data1 = n
                event.data2 = 0
                if n in self.fire.PlayingNotes:
                    self.fire.PlayingNotes.remove(n)
                event.handled = False

        self.Refresh()

    # ==========================
    # Pad Colors
    # ==========================

    def _GetPadColor(self, pad_num):
        """Get color for a pad based on its note and state."""
        col = pad_num % PadsStride
        row = pad_num // PadsStride

        # Beat view: current playing step = bright red cursor
        stepPos = self.fire.GetChanRackStartPos() + row * 16 + col
        if stepPos == self.fire.CurStep:
            return 0xFF0000

        if col >= NM_CHROMATIC:
            return NM_COL_FUNC

        note = self.GetNoteForPad(pad_num)
        if note < 0:
            return NM_COL_OFF

        # Note currently playing/held?
        if note in self.fire.PlayingNotes:
            return NM_COL_PLAYING

        # Color by note class
        noteClass = note % 12
        if noteClass == 0:  # C = root
            return NM_COL_ROOT
        elif noteClass in NM_BLACK_KEYS:
            return NM_COL_BLACK
        else:
            return NM_COL_WHITE

    # ==========================
    # Refresh
    # ==========================

    def Refresh(self):
        """Refresh all 64 pads with piano layout colors."""
        if not device.isAssigned():
            return

        dataOut = bytearray(0)

        for row in range(PadsH):
            for col in range(PadsW):
                padNum = row * PadsStride + col
                color = self._GetPadColor(padNum)

                if self.fire.BtnMap[padNum] != color:
                    r = ((color >> 16) & 0xFF) >> 1
                    g = ((color >> 8) & 0xFF) >> 1
                    b = (color & 0xFF) >> 1
                    dataOut.append(padNum)
                    dataOut.append(r & 0x7F)
                    dataOut.append(g & 0x7F)
                    dataOut.append(b & 0x7F)
                    self.fire.BtnMap[padNum] = color

        if len(dataOut) > 0:
            screen.unBlank(True)
            self.fire.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)

    # ==========================
    # OLED Display
    # ==========================

    def _DisplayNoteOLED(self, midiNote):
        """Show note name + octave on OLED."""
        noteName = NM_NOTE_NAMES[midiNote % 12]
        octave = (midiNote // 12) - 2
        if self.ChordMode:
            chordName = self.fire.chord_select_handler.GetCurrentChordName()
            self.fire.DisplayTimedText(noteName + str(octave) + ' ' + chordName)
        else:
            self.fire.DisplayTimedText(noteName + str(octave))

    # ==========================
    # Beat Indicators (IDTrackSel1-4)
    # ==========================

    def OnUpdateBeatIndicator(self, value):
        """Update IDTrackSel1-4 LEDs as beat indicators.
        Progressive fill: green for normal bars, red for last bar."""
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
        """Called when Piano mode becomes active."""
        self.fire.ClearBtnMap()
        self._heldNotes.clear()
        self._beatCount = 0
        self._barCount = 0
        self.Refresh()

    def OnDeactivate(self):
        """Called when leaving Piano mode."""
        self._heldNotes.clear()
        self._ResetBeatIndicators()
