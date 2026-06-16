# Chord Select Mode for Akai Fire
# Displays chord names on 64 pads as a 16x4 pixel matrix
# Jog wheel navigates between chord types
# Selected chord is applied in StepEdit mode

import device
import channels
import utils

from fire_modules.constants import *
from fire_modules.chord_data import CHORD_TYPES, render_text_to_bitmap, get_text_pixel_width

# Pad colors for chord display
CS_COL_OFF = 0x000000      # pixel OFF

# Color per chord family
CS_CHORD_COLORS = {
    'MAJ':   0xFF0000,   # red
    'MIN':   0xFF6600,   # orange
    'DIM':   0x0044FF,   # blue
    'AUG':   0x00FF00,   # green
    'SUS':   0xFFFF00,   # yellow
    'DOM':   0xAA00FF,   # purple
    'M7B5':  0x0088FF,   # light blue
    'ADD':   0x00FFCC,   # cyan
    'MADD':  0x00CCAA,   # teal
    '5TH':   0xFF00AA,   # pink
    '6TH':   0xFF0088,   # hot pink
    'M6TH':  0xFF4488,   # soft pink
    '9TH':   0x00FFCC,   # cyan
    'M9TH':  0x00CCFF,   # sky blue
    'MMAJ':  0xFF4400,   # dark orange
}

def _get_chord_color(name):
    """Get the color for a chord name based on its family."""
    # Exact match first
    if name in CS_CHORD_COLORS:
        return CS_CHORD_COLORS[name]
    # Prefix match (e.g. MAJ7 matches MAJ, MIN7 matches MIN)
    for prefix in ('MMAJ', 'MADD', 'M9TH', 'M7B5', 'M6TH', 'MIN', 'MAJ', 'DIM', 'AUG', 'SUS', 'DOM', 'ADD', '5TH', '6TH', '9TH'):
        if name.startswith(prefix):
            return CS_CHORD_COLORS[prefix]
    return 0xFF6600  # fallback orange

# Scroll speed (idle ticks between scroll steps)
CS_SCROLL_SPEED = 8


class ChordSelectMode:
    def __init__(self, fire):
        self.fire = fire
        self.ChordIndex = 0          # index into CHORD_TYPES
        self.ScrollOffset = 0        # current scroll position for text
        self.ScrollTimer = 0         # idle tick counter for scrolling
        self.ScrollPaused = 0        # pause at start/end of scroll
        self._lastChordIndex = -1    # for detecting changes

    # ==========================
    # Chord Access
    # ==========================

    def GetCurrentChordName(self):
        """Get the name of the currently selected chord."""
        return CHORD_TYPES[self.ChordIndex][0]

    def GetCurrentChordIntervals(self):
        """Get the interval list of the currently selected chord."""
        return CHORD_TYPES[self.ChordIndex][1]

    def GetChordCount(self):
        return len(CHORD_TYPES)

    # ==========================
    # Navigation (Jog Wheel)
    # ==========================

    def ScrollChord(self, direction):
        """Move to next/previous chord type. Returns display text."""
        self.ChordIndex = (self.ChordIndex + direction) % len(CHORD_TYPES)
        self.ScrollOffset = 0
        self.ScrollTimer = 0
        self.ScrollPaused = CS_SCROLL_SPEED * 3  # pause at start
        self.Refresh()
        return 'Chord: ' + self.GetCurrentChordName()

    # ==========================
    # Pad Display (16x4 bitmap matrix)
    # ==========================

    def Refresh(self):
        """Refresh all 64 pads with the chord name as pixel text."""
        if not device.isAssigned():
            return

        name = self.GetCurrentChordName()
        bitmap = render_text_to_bitmap(name, self.ScrollOffset)

        dataOut = bytearray(0)

        for phys_row in range(4):        # rows 0-3
            for phys_col in range(16):   # cols 0-15
                padNum = phys_row * PadsStride + phys_col
                pixel = bitmap[phys_row][phys_col] if phys_row < len(bitmap) else 0

                if pixel:
                    color = _get_chord_color(name)
                else:
                    color = CS_COL_OFF

                if self.fire.BtnMap[padNum] != color:
                    r = int(((color >> 16) & 0xFF) * 0.3) >> 1
                    g = int(((color >> 8) & 0xFF) * 0.3) >> 1
                    b = int((color & 0xFF) * 0.3) >> 1
                    dataOut.append(padNum)
                    dataOut.append(r & 0x7F)
                    dataOut.append(g & 0x7F)
                    dataOut.append(b & 0x7F)
                    self.fire.BtnMap[padNum] = color

        if len(dataOut) > 0:
            import screen
            screen.unBlank(True)
            self.fire.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)

    # ==========================
    # OnIdle — text scrolling
    # ==========================

    def OnIdle(self):
        """Handle text scrolling animation on pads."""
        name = self.GetCurrentChordName()
        textWidth = get_text_pixel_width(name)

        if textWidth <= 16:
            # Text fits, no scrolling needed
            if self.ScrollOffset != 0:
                self.ScrollOffset = 0
                self.Refresh()
            return

        # Scrolling needed
        self.ScrollTimer += 1
        if self.ScrollTimer < CS_SCROLL_SPEED:
            return
        self.ScrollTimer = 0

        # Pause at boundaries
        if self.ScrollPaused > 0:
            self.ScrollPaused -= 1
            return

        self.ScrollOffset += 1
        if self.ScrollOffset > textWidth - 16:
            # Reached end, pause then reset
            self.ScrollOffset = 0
            self.ScrollPaused = CS_SCROLL_SPEED * 3

        self.Refresh()

    # ==========================
    # Mode Activation
    # ==========================

    def OnActivate(self):
        """Called when Chord Select mode becomes active."""
        self.fire.ClearBtnMap()
        self.ScrollOffset = 0
        self.ScrollTimer = 0
        self.ScrollPaused = CS_SCROLL_SPEED * 3
        self.Refresh()

    def OnDeactivate(self):
        """Called when leaving Chord Select mode."""
        pass

    # ==========================
    # OLED Display
    # ==========================

    def GetDisplayText(self):
        """Get text for the OLED display."""
        name = self.GetCurrentChordName()
        intervals = self.GetCurrentChordIntervals()
        noteNames = []
        for iv in intervals:
            noteNames.append(str(iv))
        return 'Chord: ' + name + chr(13) + 'Int: ' + '-'.join(noteNames)
