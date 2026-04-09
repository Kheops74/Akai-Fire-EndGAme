#   name=AKAI FL Studio Fire - Performance Mode
#   Mode Performance : 64 pads = mute de 64 éléments
#   (mixer tracks / playlist tracks / channel rack) selon fenêtre active
#   Synchronisation à la mesure configurable via jog wheel
#   Clignotement des pads pending, changement d'état en fin de cycle

import mixer
import playlist
import channels
import patterns
import transport
import general
import device
import screen
import ui
import utils

from midi import *
from fire_modules.mode_base import FireModeBase
from fire_modules.constants import *

# Source modes
SRC_MIXER = 0
SRC_CHANNEL = 1
SRC_PLAYLIST = 2
SRC_PATTERN = 3

SRC_NAMES = ['Mixer', 'Channel Rack', 'Playlist', 'Patterns']

# Sync bar options
SYNC_OPTIONS = [1, 2, 4, 8]

# Dim factor for muted pads
DIM_FACTOR = 0.35
# Blink speed (in idle cycles, ~50ms each)
BLINK_SPEED = 8
BLINK_SPEED_PS = 4  # faster blink for Play & Stop pads

# Default color when no track color available
COL_DEFAULT_ON = 0x00FF00
COL_DEFAULT_OFF = 0x002200
COL_OFF = 0x000000


class PerfMode(FireModeBase):
    """Mode Performance : 64 pads mute/unmute avec sync mesure."""

    def __init__(self, fire_device):
        super().__init__(fire_device)
        self.SyncBarsIndex = 0      # index into SYNC_OPTIONS (0=1bar, 1=2bars, etc.)
        self.SourceMode = SRC_MIXER  # 0=Mixer, 1=ChannelRack, 2=Playlist, 3=Pattern
        self.PadOffsetPerSource = {SRC_MIXER: 0, SRC_CHANNEL: 0, SRC_PLAYLIST: 0, SRC_PATTERN: 0}
        self.PendingPerSource = {SRC_MIXER: {}, SRC_CHANNEL: {}, SRC_PLAYLIST: {}, SRC_PATTERN: {}}
        self.PlayAndStopPerSource = {SRC_MIXER: {}, SRC_CHANNEL: {}, SRC_PLAYLIST: {}, SRC_PATTERN: {}}
        self.BlinkCounter = 0        # counter for blink animation
        self._wasPlaying = False     # track play state transitions
        self._lastSongPos = 0       # previous songPos to detect wrap-around
        self._lastBoundaryIdx = 0   # last boundary index for sync (SyncBars)
        self._playheadPad = -1      # current pad index (0-63) for playhead overlay
        self._pendingPattern = -1   # target pattern for SRC_PATTERN mode (-1 = none)
        self._beatCount = 0         # beat counter for beat indicators

    @property
    def SyncBars(self):
        return SYNC_OPTIONS[self.SyncBarsIndex]

    @property
    def PadOffset(self):
        return self.PadOffsetPerSource[self.SourceMode]

    @PadOffset.setter
    def PadOffset(self, value):
        self.PadOffsetPerSource[self.SourceMode] = value

    @property
    def PendingChanges(self):
        return self.PendingPerSource[self.SourceMode]

    @property
    def PlayAndStop(self):
        return self.PlayAndStopPerSource[self.SourceMode]

    # ==========================
    # Element count & state
    # ==========================

    def _GetElementCount(self, source=None):
        """Return total number of elements for given source (default: current)."""
        src = source if source is not None else self.SourceMode
        if src == SRC_MIXER:
            return mixer.trackCount() - 1  # exclude master track (index 0)
        elif src == SRC_CHANNEL:
            return channels.channelCount()
        elif src == SRC_PLAYLIST:
            return playlist.trackCount()
        elif src == SRC_PATTERN:
            return patterns.patternCount()
        return 0

    def _IsElementMuted(self, index, source=None):
        """Return True if element at index is muted."""
        src = source if source is not None else self.SourceMode
        try:
            if src == SRC_MIXER:
                return mixer.isTrackMuted(index + 1)  # mixer tracks are 1-indexed
            elif src == SRC_CHANNEL:
                return channels.isChannelMuted(index)
            elif src == SRC_PLAYLIST:
                return playlist.isTrackMuted(index + 1)  # playlist tracks are 1-indexed
            elif src == SRC_PATTERN:
                return (index + 1) != patterns.patternNumber()
        except:
            return False
        return False

    def _MuteElement(self, index, source=None):
        """Toggle mute on element at index."""
        src = source if source is not None else self.SourceMode
        try:
            if src == SRC_MIXER:
                mixer.muteTrack(index + 1)  # 1-indexed
            elif src == SRC_CHANNEL:
                channels.muteChannel(index)
            elif src == SRC_PLAYLIST:
                playlist.muteTrack(index + 1)  # 1-indexed
            elif src == SRC_PATTERN:
                patterns.jumpToPattern(index + 1)  # 1-indexed
        except Exception as e:
            print('PerfMode mute error: ' + str(e))

    def _GetElementColor(self, index, source=None):
        """Get the native FL Studio color for the element."""
        src = source if source is not None else self.SourceMode
        try:
            if src == SRC_MIXER:
                return mixer.getTrackColor(index + 1)  # 1-indexed
            elif src == SRC_CHANNEL:
                return channels.getChannelColor(index)
            elif src == SRC_PLAYLIST:
                return playlist.getTrackColor(index + 1)  # 1-indexed
            elif src == SRC_PATTERN:
                return patterns.getPatternColor(index + 1)  # 1-indexed
        except:
            return COL_DEFAULT_ON
        return COL_DEFAULT_ON

    def _GetElementName(self, index, source=None):
        """Get the name of the element."""
        src = source if source is not None else self.SourceMode
        try:
            if src == SRC_MIXER:
                return mixer.getTrackName(index + 1)
            elif src == SRC_CHANNEL:
                return channels.getChannelName(index)
            elif src == SRC_PLAYLIST:
                return playlist.getTrackName(index + 1)
            elif src == SRC_PATTERN:
                return patterns.getPatternName(index + 1)
        except:
            return '?'
        return '?'

    # ==========================
    # Pad events
    # ==========================

    def OnPadEvent(self, event, pad_num):
        """Handle pad press in Performance mode."""
        if event.data2 == 0:
            event.handled = True
            return  # ignore release

        row = pad_num // PadsStride
        col = pad_num % PadsStride
        if col >= 16 or row >= 4:
            event.handled = True
            return

        elementIndex = self.PadOffset + row * 16 + col
        elementCount = self._GetElementCount()
        if elementIndex >= elementCount:
            event.handled = True
            return

        if self.fire.AltHeld and self.SourceMode != SRC_PATTERN:
            # Alt+Pad: Play & Stop mode (toggle for N bars then auto re-toggle)
            if elementIndex in self.PlayAndStop:
                # Cancel existing Play & Stop
                del self.PlayAndStop[elementIndex]
                name = self._GetElementName(elementIndex)
                self.fire.DisplayTimedText(name + chr(13) + 'P&S Cancelled')
            else:
                currentMuted = self._IsElementMuted(elementIndex)
                try:
                    ppq = general.getRecPPQ()
                    ticksPerBar = ppq * 4
                except:
                    ticksPerBar = 96 * 4
                self.PlayAndStop[elementIndex] = {
                    'state': 'waiting',
                    'ticks_target': ticksPerBar * self.SyncBars,
                    'ticks_elapsed': 0,
                    'original_muted': currentMuted,
                    'last_songpos': transport.getSongPos(SONGLENGTH_ABSTICKS)
                }
                # Remove from normal pending if it was there
                if elementIndex in self.PendingChanges:
                    del self.PendingChanges[elementIndex]
                name = self._GetElementName(elementIndex)
                action = 'UNMUTE' if currentMuted else 'MUTE'
                self.fire.DisplayTimedText(name + chr(13) + 'P&S ' + action + ' ' + str(self.SyncBars) + 'bar')
            self.Refresh()
        elif self.fire.ShiftHeld and transport.isPlaying():
            # Shift+Pad: immediate action, bypass pending (all modes)
            if self.SourceMode == SRC_PATTERN:
                patNum = elementIndex + 1
                patterns.jumpToPattern(patNum)
                self._pendingPattern = -1
                self.fire.DisplayTimedText(patterns.getPatternName(patNum) + chr(13) + 'Instant')
            else:
                self._MuteElement(elementIndex)
                if elementIndex in self.PendingChanges:
                    del self.PendingChanges[elementIndex]
                if elementIndex in self.PlayAndStop:
                    del self.PlayAndStop[elementIndex]
                muted = self._IsElementMuted(elementIndex)
                name = self._GetElementName(elementIndex)
                self.fire.DisplayTimedText(name + chr(13) + ('MUTED' if muted else 'ACTIVE') + ' (instant)')
            self.Refresh()
        elif self.SourceMode == SRC_PATTERN:
            # Pattern mode: select pattern to play next
            patNum = elementIndex + 1  # 1-indexed
            if not transport.isPlaying():
                patterns.jumpToPattern(patNum)
                self._pendingPattern = -1
                self.fire.DisplayTimedText(patterns.getPatternName(patNum))
            else:
                # Normal pending
                if self._pendingPattern == patNum:
                    self._pendingPattern = -1
                    self.fire.DisplayTimedText(patterns.getPatternName(patNum) + chr(13) + 'Cancelled')
                else:
                    self._pendingPattern = patNum
                    try:
                        songPos = transport.getSongPos(SONGLENGTH_ABSTICKS)
                        ppq = general.getRecPPQ()
                        patLenBeats = patterns.getPatternLength(patterns.patternNumber())
                        patLenTicks = patLenBeats * ppq
                        if patLenTicks > 0:
                            self._lastBoundaryIdx = songPos // patLenTicks
                    except:
                        pass
                    patBars = max(patterns.getPatternLength(patterns.patternNumber()) // 4, 1)
                    self.fire.DisplayTimedText(patterns.getPatternName(patNum) + chr(13) + 'Next (' + str(patBars) + ' bar)')
        elif not transport.isPlaying():
            # Immediate mute when not playing
            self._MuteElement(elementIndex)
            muted = self._IsElementMuted(elementIndex)
            name = self._GetElementName(elementIndex)
            self.fire.DisplayTimedText(name + chr(13) + ('MUTED' if muted else 'ACTIVE'))
        else:
            # Toggle pending state
            if elementIndex in self.PendingChanges:
                # Cancel pending
                del self.PendingChanges[elementIndex]
                name = self._GetElementName(elementIndex)
                self.fire.DisplayTimedText(name + chr(13) + 'Pending OFF')
            else:
                # Add pending: target = opposite of current state
                currentMuted = self._IsElementMuted(elementIndex)
                self.PendingChanges[elementIndex] = not currentMuted
                # Snapshot current boundary so we wait for the NEXT crossing
                if len(self.PendingChanges) == 1:
                    try:
                        songPos = transport.getSongPos(SONGLENGTH_ABSTICKS)
                        ppq = general.getRecPPQ()
                        ticksPerBar = ppq * 4
                        boundaryTicks = ticksPerBar * self.SyncBars
                        if boundaryTicks > 0:
                            self._lastBoundaryIdx = songPos // boundaryTicks
                    except:
                        pass
                name = self._GetElementName(elementIndex)
                target = 'MUTE' if (not currentMuted) else 'UNMUTE'
                self.fire.DisplayTimedText(name + chr(13) + 'Pending ' + target)

        self.Refresh()
        event.handled = True

    # ==========================
    # Jog wheel: change sync bars
    # ==========================

    def OnJogWheel(self, event):
        """Jog wheel changes sync bars (1/2/4/8)."""
        if event.data2 == 1:
            self.SyncBarsIndex = min(self.SyncBarsIndex + 1, len(SYNC_OPTIONS) - 1)
        elif event.data2 == 127:
            self.SyncBarsIndex = max(self.SyncBarsIndex - 1, 0)
        self.fire.DisplayTimedText('Sync: ' + str(self.SyncBars) + ' bar' + ('s' if self.SyncBars > 1 else ''))
        return True

    # ==========================
    # Jog push: toggle source mode
    # ==========================

    def OnJogPush(self):
        """Toggle source mode: Mixer -> ChannelRack -> Playlist -> Pattern -> Mixer."""
        self.SourceMode = (self.SourceMode + 1) % 4
        self.fire.ClearBtnMap()
        self.fire.DisplayTimedText('Perf: ' + SRC_NAMES[self.SourceMode])
        self.Refresh()

    # ==========================
    # OnIdle: sync check + blink
    # ==========================

    def OnIdle(self):
        """Called periodically. Check sync and apply pending changes."""
        self.BlinkCounter = (self.BlinkCounter + 1) % (BLINK_SPEED * 2)

        playing = transport.isPlaying()

        # Detect play state transitions
        if playing and not self._wasPlaying:
            # Just started playing: reset tracking
            self._lastSongPos = transport.getSongPos(SONGLENGTH_ABSTICKS)
            self._lastBoundaryIdx = 0
        elif not playing and self._wasPlaying:
            # Just stopped: apply all pending changes and cancel all P&S for ALL sources
            self._ApplyAllPending()
            self._CancelAllPlayAndStop()
            self.Refresh()
        self._wasPlaying = playing

        if not playing:
            return

        # Always update playhead overlay when playing
        try:
            songPos = transport.getSongPos(SONGLENGTH_ABSTICKS)
            if songPos < 0:
                return

            ppq = general.getRecPPQ()
            ticksPerBar = ppq * 4  # assumes 4/4
            if ticksPerBar <= 0:
                return

            # Playhead: 16 pads = 1 bar, window = 4 bars
            windowTicks = ticksPerBar * 4
            stepTicks = ticksPerBar // 16
            if stepTicks > 0:
                rel = songPos % windowTicks
                newPad = int(rel // stepTicks)
                if newPad != self._playheadPad:
                    self._playheadPad = newPad
                    self.Refresh()

            # Boundary: pattern length for SRC_PATTERN, SyncBars for others
            if self.SourceMode == SRC_PATTERN:
                patLenBeats = patterns.getPatternLength(patterns.patternNumber())
                boundaryTicks = patLenBeats * ppq if patLenBeats > 0 else ticksPerBar * self.SyncBars
            else:
                boundaryTicks = ticksPerBar * self.SyncBars

            if boundaryTicks > 0:
                boundaryIdx = songPos // boundaryTicks

                boundaryChanged = (boundaryIdx != self._lastBoundaryIdx) or (songPos < self._lastSongPos)

                # Apply pending changes for ALL sources at boundary
                if boundaryChanged:
                    self._ApplyAllPending()

                # Play & Stop logic for ALL sources: tick-based
                self._ProcessAllPlayAndStop(songPos)

                self._lastBoundaryIdx = boundaryIdx

            self._lastSongPos = songPos
        except Exception as e:
            print('PerfMode sync error: ' + str(e))

    def _ApplyAllPending(self):
        """Apply pending mute/unmute changes for ALL sources."""
        applied = False
        # Pattern pending (global)
        if self._pendingPattern >= 0:
            patterns.jumpToPattern(self._pendingPattern)
            self._pendingPattern = -1
            applied = True
        # Pending changes per source
        for src in range(4):
            pending = self.PendingPerSource[src]
            if len(pending) > 0:
                for elementIndex, targetMuted in list(pending.items()):
                    currentMuted = self._IsElementMuted(elementIndex, src)
                    if currentMuted != targetMuted:
                        self._MuteElement(elementIndex, src)
                pending.clear()
                applied = True
        if applied:
            self.Refresh()

    def _ProcessAllPlayAndStop(self, songPos):
        """Process Play & Stop entries for ALL sources using absolute tick counting."""
        anyRemoved = False
        for src in range(4):
            psDict = self.PlayAndStopPerSource[src]
            if len(psDict) == 0:
                continue
            toRemove = []
            for elemIdx, info in list(psDict.items()):
                # Calculate ticks elapsed since last check
                lastPos = info['last_songpos']
                if songPos >= lastPos:
                    delta = songPos - lastPos
                else:
                    # Song/pattern looped: estimate delta from pattern length
                    try:
                        ppq = general.getRecPPQ()
                        patLenBeats = patterns.getPatternLength(patterns.patternNumber())
                        patLenTicks = patLenBeats * ppq if patLenBeats > 0 else ppq * 4
                    except:
                        patLenTicks = info['ticks_target']
                    delta = (patLenTicks - lastPos) + songPos
                info['last_songpos'] = songPos
                info['ticks_elapsed'] += delta

                if info['ticks_elapsed'] >= info['ticks_target']:
                    if info['state'] == 'waiting':
                        self._MuteElement(elemIdx, src)
                        info['state'] = 'playing'
                        info['ticks_elapsed'] = 0
                    elif info['state'] == 'playing':
                        self._MuteElement(elemIdx, src)
                        toRemove.append(elemIdx)
            for elemIdx in toRemove:
                del psDict[elemIdx]
            if len(toRemove) > 0:
                anyRemoved = True
        if anyRemoved:
            self.Refresh()

    def _CancelAllPlayAndStop(self):
        """Cancel all Play & Stop entries for ALL sources, restoring original states."""
        for src in range(4):
            psDict = self.PlayAndStopPerSource[src]
            for elemIdx, info in list(psDict.items()):
                if info['state'] == 'playing':
                    self._MuteElement(elemIdx, src)
            psDict.clear()

    # ==========================
    # Refresh LEDs
    # ==========================

    def _BoostColor(self, color):
        """Boost saturation/brightness of an FL color, like ScaleColor does for other modes."""
        h, s, v = utils.RGBToHSVColor(color)
        boosted, h, s, v = self.fire.ScaleColor(1.0, h, s, v)
        return boosted

    def _DimColor(self, color, factor):
        """Dim a 0xRRGGBB color by factor (0.0-1.0)."""
        r = int(((color >> 16) & 0xFF) * factor)
        g = int(((color >> 8) & 0xFF) * factor)
        b = int((color & 0xFF) * factor)
        return (r << 16) | (g << 8) | b

    def Refresh(self):
        """Refresh all 64 pads with current state."""
        if not device.isAssigned():
            return

        elementCount = self._GetElementCount()
        blinkOn = self.BlinkCounter < BLINK_SPEED

        dataOut = bytearray(0)

        for row in range(4):
            for col in range(16):
                pad_num = row * PadsStride + col
                elementIndex = self.PadOffset + row * 16 + col

                if elementIndex >= elementCount:
                    # No element -> off
                    c = COL_OFF
                else:
                    baseColor = self._BoostColor(self._GetElementColor(elementIndex))
                    muted = self._IsElementMuted(elementIndex)
                    if self.SourceMode == SRC_PATTERN:
                        isPending = (elementIndex + 1) == self._pendingPattern
                    else:
                        isPending = elementIndex in self.PendingChanges
                    isPlayAndStop = elementIndex in self.PlayAndStop
                    blinkOnPS = self.BlinkCounter < BLINK_SPEED_PS or (self.BlinkCounter >= BLINK_SPEED and self.BlinkCounter < BLINK_SPEED + BLINK_SPEED_PS)

                    if isPlayAndStop:
                        # P&S: fast blink between white and base color
                        psInfo = self.PlayAndStop[elementIndex]
                        if psInfo['state'] == 'waiting':
                            # Waiting phase: fast blink between dim and white
                            c = 0xFFFFFF if blinkOnPS else self._DimColor(baseColor, DIM_FACTOR)
                        else:
                            # Playing phase: fast blink between full color and white
                            c = 0xFFFFFF if blinkOnPS else baseColor
                    elif isPending:
                        # Blink: alternate between muted dim and active bright
                        if blinkOn:
                            c = baseColor if muted else self._DimColor(baseColor, DIM_FACTOR)
                        else:
                            c = self._DimColor(baseColor, DIM_FACTOR) if muted else baseColor
                    else:
                        if muted:
                            c = self._DimColor(baseColor, DIM_FACTOR)
                        else:
                            c = baseColor

                # Playhead overlay: highlight current pad in bright white
                if pad_num == self._playheadPad:
                    c = 0xFFFFFF

                # Write pad color
                r = ((c >> 16) & 0xFF) >> 1
                g = ((c >> 8) & 0xFF) >> 1
                b = (c & 0xFF) >> 1
                dataOut.append(pad_num)
                dataOut.append(r & 0x7F)
                dataOut.append(g & 0x7F)
                dataOut.append(b & 0x7F)

        if len(dataOut) > 0:
            screen.unBlank(True)
            self.fire.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)

        # Mute buttons: light up current source, blink if other source has pending/P&S
        blinkOn = self.BlinkCounter < BLINK_SPEED
        for i in range(4):
            if i == self.SourceMode:
                self.fire.SendCC(IDMute1 + i, SingleColorFull)
            elif len(self.PendingPerSource[i]) > 0 or len(self.PlayAndStopPerSource[i]) > 0:
                # Non-active source with pending actions: blink
                self.fire.SendCC(IDMute1 + i, SingleColorFull if blinkOn else SingleColorOff)
            else:
                self.fire.SendCC(IDMute1 + i, SingleColorOff)

        # TrackSel LEDs: green for active source, red for others
        self._RefreshSourceLEDs()

    # ==========================
    # Source LEDs (IDTrackSel1-4)
    # ==========================

    def _RefreshSourceLEDs(self):
        """IDTrackSel LEDs: green for active source, red for others."""
        for i in range(4):
            if i == self.SourceMode:
                self.fire.SendCC(IDTrackSel1 + i, SingleColorFull)  # green
            else:
                self.fire.SendCC(IDTrackSel1 + i, SingleColorHalfBright)  # red

    def OnUpdateBeatIndicator(self, value):
        """Refresh source LEDs on beat update."""
        self._RefreshSourceLEDs()

    # ==========================
    # Activate / Deactivate
    # ==========================

    def OnActivate(self):
        """Called when Performance mode becomes active."""
        for src in range(4):
            self.PendingPerSource[src].clear()
            self.PlayAndStopPerSource[src].clear()
        self._pendingPattern = -1
        self.BlinkCounter = 0
        self._lastBoundaryIdx = 0
        self._beatCount = 0
        self._wasPlaying = transport.isPlaying()
        if self._wasPlaying:
            self._lastSongPos = transport.getSongPos(SONGLENGTH_ABSTICKS)
        self.fire.ClearBtnMap()
        syncTxt = 'Auto' if self.SourceMode == SRC_PATTERN else str(self.SyncBars) + ' bar' + ('s' if self.SyncBars > 1 else '')
        self.fire.DisplayTimedText('Perf: ' + SRC_NAMES[self.SourceMode] + chr(13) + 'Sync: ' + syncTxt)
        self.Refresh()

    def OnDeactivate(self):
        """Called when leaving Performance mode."""
        # Apply all pending changes for ALL sources
        self._ApplyAllPending()
        # Cancel all Play & Stop for ALL sources (restore original states)
        self._CancelAllPlayAndStop()
        # Reset source LEDs
        for i in range(4):
            self.fire.SendCC(IDTrackSel1 + i, SingleColorOff)

    # ==========================
    # Grid L/R: page offset
    # ==========================

    def OnBankLR(self, direction):
        """Grid L/R changes pad offset by 64."""
        self.PadOffset = max(0, self.PadOffset + 64 * direction)
        maxOfs = max(0, self._GetElementCount() - 64)
        self.PadOffset = min(self.PadOffset, maxOfs)
        self.PendingChanges.clear()
        self.fire.ClearBtnMap()
        self.fire.DisplayTimedText('Page ' + str(self.PadOffset // 64 + 1) + chr(13) + str(self.PadOffset + 1) + '-' + str(min(self.PadOffset + 64, self._GetElementCount())))
        self.Refresh()

    # ==========================
    # Display zone (kept for compatibility)
    # ==========================

    def OnDisplayZone(self):
        """Display zone placeholder for compatibility."""
        pass
