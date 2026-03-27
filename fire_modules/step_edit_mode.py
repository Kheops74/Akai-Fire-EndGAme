#   name=AKAI FL Studio Fire - Step Edit Mode (Piano Roll Vertical)
#   Séquenceur vertical : 4 steps x 16 pitches sur un seul instrument
#   Inspiré du ZaquSequencer - grille interne autonome

import channels
import patterns
import transport
import device
import utils
import ui
import general
import mixer
import os
import struct
import json
import time

from midi import *
from fire_modules.mode_base import FireModeBase
from fire_modules.constants import *
import harmonicScales

# ---- Step Edit Constants ----

# Visible grid dimensions (Akai Fire turned 90°)
# Physical layout: 16 cols x 4 rows
# Vertical mapping: col = pitch (16 visible), row = step (4 visible)
SE_VISIBLE_STEPS = 4       # 4 rows = 4 steps visible at once
SE_VISIBLE_PITCHES = 16    # 16 cols = 16 pitches visible at once
SE_MAX_STEPS = 256         # max steps in sequence (expandable)
SE_DEFAULT_STEPS = 64      # default pattern length in steps (4 bars)
SE_DEFAULT_VELOCITY = 100  # default note velocity (0-127)
SE_DEFAULT_LENGTH = 1      # default note length in steps
SE_DEFAULT_DELAY = 0       # default time offset (0-127)

# Colors (RGB packed as 0xRRGGBB, will be halved for pad output)
SE_COL_OFF = 0x000000           # empty pad
SE_COL_NOTE_ON = 0x00FF00       # active note (green)
SE_COL_NOTE_PLAYING = 0xFFFFFF  # currently playing step (white flash)
SE_COL_NOTE_EDIT = 0xFF8800     # note selected for editing (orange blink)
SE_COL_OUT_OF_SCALE = 0x181818  # note not in current scale (dark grey)
SE_COL_ROOT_NOTE = 0x0040FF     # root note row (blue tint)
SE_COL_IN_SCALE = 0x101010      # in-scale empty white key (very dim white)
SE_COL_BLACK_KEY = 0x100010     # black key of piano (very dim violet)
SE_COL_STEP_MUTED = 0x220000    # muted step column (dark red tint)
SE_COL_PLAYHEAD = 0x333333      # playhead column dim overlay

# Scale intervals (semitones from root, -1 = end marker)
# We reuse harmonicScales module for scale definitions

class NoteData:
    """Represents a single note event in the internal grid."""
    __slots__ = ('velocity', 'length', 'delay')

    def __init__(self, velocity=SE_DEFAULT_VELOCITY, length=SE_DEFAULT_LENGTH, delay=SE_DEFAULT_DELAY):
        self.velocity = velocity  # 0-127
        self.length = length      # in steps (1 = one step, 2 = two steps, etc.)
        self.delay = delay        # time offset within step (0-127, 64 = center)


class StepEditMode(FireModeBase):
    """Piano Roll Vertical mode for Akai Fire.

    Grid layout (Akai turned 90°, USB port on top):
    - Physical column (0-15) = pitch (bottom=low, top=high)
    - Physical row (0-3) = step in time (left=first, right=last)

    Internal coordinate system:
    - step: temporal position (0 to PatternLength-1)
    - pitch: MIDI note number (0-127)
    """

    def __init__(self, fire_device):
        super().__init__(fire_device)

        # ---- Grid State ----
        # Internal grid: dict of {step_index: {midi_pitch: NoteData}}
        self.Grid = {}
        self.PatternLength = SE_DEFAULT_STEPS  # total steps in pattern

        # ---- View State ----
        self.StepOffset = 0       # first visible step (scroll position)
        self.PitchOffset = 48     # lowest visible MIDI pitch (C4 = 48)
        self.CurrentStep = -1     # playhead position (-1 = stopped)

        # ---- Scale State ----
        self.ScaleIndex = -1      # -1 = chromatic (no scale filter), 0+ = harmonicScales index
        self.RootNote = 0         # root note (0=C, 1=C#, ... 11=B)

        # ---- Edit State ----
        self.EditMode = False      # True = edit mode active (pads blink, knobs edit params)
        self.SelectedPads = []     # list of (step, pitch) tuples currently selected for editing
        self.StepMuted = [False] * SE_MAX_STEPS  # per-step mute

        # ---- Playback State ----
        self.PlayingNotes = []     # legacy compat
        self.ActiveNotes = []      # list of (chanIndex, pitch, offTick) currently sounding
        self.PendingNotes = []     # list of (onTick, chanIndex, pitch, velocity, offTick) waiting to trigger
        self.LastPlayedStep = -1   # last step that was played (to avoid retriggering)
        self.LastProcessedTick = -1  # last tick processed for scheduling
        self.LastMonoSyncSignature = None
        self.LastMonoSyncChan = -1
        self.LastMonoSyncPat = -1
        self.ChordMode = False
        self.AutoChord = False   # True = auto-add chord intervals when placing notes
        self._gridDirty = False  # True = user modified grid locally, skip reverse sync
        self._wasPlaying = False  # track transport state transitions for FL sync
        self._prScrollAccum = 0   # accumulator for piano roll scroll (ui.up scrolls ~3 notes per call)
        self.LastFileError = ''

    # ==========================
    # Grid Data Management
    # ==========================

    def SetNote(self, step, pitch, velocity=SE_DEFAULT_VELOCITY, length=SE_DEFAULT_LENGTH, delay=SE_DEFAULT_DELAY):
        """Add or update a note at (step, pitch)."""
        if step not in self.Grid:
            self.Grid[step] = {}
        elif not self.ChordMode:
            self.Grid[step].clear()
        self.Grid[step][pitch] = NoteData(velocity, length, delay)
        self._gridDirty = True

    def RemoveNote(self, step, pitch):
        """Remove a note at (step, pitch)."""
        if step in self.Grid and pitch in self.Grid[step]:
            del self.Grid[step][pitch]
            if len(self.Grid[step]) == 0:
                del self.Grid[step]
            self._gridDirty = True

    def HasNote(self, step, pitch):
        """Check if a note exists at (step, pitch)."""
        return step in self.Grid and pitch in self.Grid[step]

    def GetNote(self, step, pitch):
        """Get NoteData at (step, pitch), or None."""
        if step in self.Grid and pitch in self.Grid[step]:
            return self.Grid[step][pitch]
        return None

    def GetNotesAtStep(self, step):
        """Get all notes at a given step as dict {pitch: NoteData}."""
        return self.Grid.get(step, {})

    def ClearGrid(self):
        """Clear all notes from the grid."""
        self.Grid.clear()

    def ToggleNote(self, step, pitch):
        """Toggle a note ON/OFF at (step, pitch). Returns True if note was added."""
        if self.HasNote(step, pitch):
            self.RemoveNote(step, pitch)
            return False
        else:
            self.SetNote(step, pitch)
            return True

    def ToggleChordMode(self):
        self.ChordMode = not self.ChordMode
        if not self.ChordMode:
            self.SyncFromChannelRackMono(True)
        self.fire.ClearBtnMap()
        self.Refresh()
        if self.ChordMode:
            return 'StepEdit: CHORD'
        return 'StepEdit: MONO'

    def _GetActiveChordIntervals(self):
        """Get the chord intervals to apply when adding notes.
        Returns the interval list from chord_select_handler if AutoChord is on,
        or [0] for single/manual poly mode."""
        if self.AutoChord:
            try:
                return self.fire.chord_select_handler.GetCurrentChordIntervals()
            except:
                pass
        return [0]

    # ==========================
    # FL Studio Sync (Hybrid)
    # ==========================

    def _SyncStepToFL(self, step):
        """Sync a single step to FL Studio channel rack.
        Always writes to FL — FL plays via gridBits at all times.
        Internal engine only adds extra poly notes in ChordMode."""
        chanIndex = channels.selectedChannel(1)
        if chanIndex < 0:
            return
        if step < 0:
            return

        try:
            self._WriteStepToFL(chanIndex, step)
            self.LastMonoSyncSignature = None
            self.LastMonoSyncChan = chanIndex
            self.LastMonoSyncPat = patterns.patternNumber()
        except Exception as e:
            print('StepEdit _SyncStepToFL error step=' + str(step) + ': ' + str(e))

    def _WriteStepToFL(self, chanIndex, step):
        """Write a single step's note data to FL channel rack grid.
        Respects StepMuted: muted steps have gridBit=0 so FL doesn't play them."""
        notes = self.GetNotesAtStep(step)
        channels.setGridBit(chanIndex, step, 0)
        if len(notes) > 0 and not self.StepMuted[step]:
            channels.setGridBit(chanIndex, step, 1)
            chanGlobalIndex = channels.getChannelIndex(chanIndex)
            patNum = patterns.patternNumber()
            lowestPitch = min(notes.keys())
            noteData = notes[lowestPitch]
            pitchValue = max(0, min(127, lowestPitch))
            channels.setStepParameterByIndex(chanGlobalIndex, patNum, step, pPitch, pitchValue, 1)
            velValue = max(0, min(128, int(noteData.velocity * 128 / 127)))
            channels.setStepParameterByIndex(chanGlobalIndex, patNum, step, pVelocity, velValue, 1)

    def _ClearAllFLGridBits(self):
        """Clear all FL grid bits so FL step sequencer does not play any notes.
        The internal playback engine handles all note output in StepEdit mode."""
        chanIndex = channels.selectedChannel(1)
        if chanIndex < 0:
            return
        try:
            for step in range(self.PatternLength):
                channels.setGridBit(chanIndex, step, 0)
        except Exception as e:
            print('StepEdit _ClearAllFLGridBits error: ' + str(e))

    def SyncAllToFL(self):
        """Write the entire internal grid to FL Studio channel rack (gridBits ON).
        Called on explicit sync (jog push) and when leaving StepEdit mode."""
        chanIndex = channels.selectedChannel(1)
        if chanIndex < 0:
            return
        try:
            general.saveUndo('Fire: StepEdit sync', UF_PR, True)
            chanGlobalIndex = channels.getChannelIndex(chanIndex)
            patNum = patterns.patternNumber()
            for step in range(self.PatternLength):
                notes = self.GetNotesAtStep(step)
                channels.setGridBit(chanIndex, step, 0)
                if len(notes) > 0 and not self.StepMuted[step]:
                    channels.setGridBit(chanIndex, step, 1)
                    lowestPitch = min(notes.keys())
                    noteData = notes[lowestPitch]
                    pitchValue = max(0, min(127, lowestPitch))
                    channels.setStepParameterByIndex(chanGlobalIndex, patNum, step, pPitch, pitchValue, 1)
                    velValue = max(0, min(128, int(noteData.velocity * 128 / 127)))
                    channels.setStepParameterByIndex(chanGlobalIndex, patNum, step, pVelocity, velValue, 1)
            self._gridDirty = False
            self.LastMonoSyncSignature = None
        except Exception as e:
            print('StepEdit SyncAllToFL error: ' + str(e))

    def _BuildMonoGridFromChannelRack(self):
        chanIndex = channels.selectedChannel(1)
        if chanIndex < 0:
            return None, None, None, None

        patNum = patterns.patternNumber()
        monoGrid = {}
        signature = []

        for step in range(self.PatternLength):
            if channels.getGridBit(chanIndex, step) > 0:
                pitch = int(channels.getStepParam(0, pPitch, chanIndex, step, 1))
                velocityRaw = int(channels.getStepParam(0, pVelocity, chanIndex, step, 1))
                pitch = max(0, min(127, pitch))
                velocity = max(1, min(127, int(round((velocityRaw * 127.0) / 128.0))))
                # Delay not read from FL — managed internally only
                monoGrid[step] = {pitch: NoteData(velocity, 1, SE_DEFAULT_DELAY)}
                signature.append((step, pitch, velocity))

        return chanIndex, patNum, tuple(signature), monoGrid

    def SyncFromChannelRackMono(self, force=False):
        if self.ChordMode and (not force):
            return False

        # If channel or pattern changed, clear dirty flag to allow re-sync
        curChan = channels.selectedChannel(1)
        curPat = patterns.patternNumber()
        if curChan != self.LastMonoSyncChan or curPat != self.LastMonoSyncPat:
            self._gridDirty = False

        if self._gridDirty and (not force):
            return False

        syncData = self._BuildMonoGridFromChannelRack()
        if syncData[0] is None:
            return False

        chanIndex, patNum, signature, monoGrid = syncData
        if (not force) and (signature == self.LastMonoSyncSignature) and (chanIndex == self.LastMonoSyncChan) and (patNum == self.LastMonoSyncPat):
            return False

        # Preserve notes of muted steps (their gridBit is 0 in FL so they won't appear in monoGrid)
        for step in range(SE_MAX_STEPS):
            if self.StepMuted[step] and step in self.Grid and step not in monoGrid:
                monoGrid[step] = self.Grid[step]
        self.Grid = monoGrid
        self._gridDirty = False  # grid now matches FL, clear dirty flag
        self.SelectedPads = [(step, pitch) for step, pitch in self.SelectedPads if step in self.Grid and pitch in self.Grid[step]]
        self.LastMonoSyncSignature = signature
        self.LastMonoSyncChan = chanIndex
        self.LastMonoSyncPat = patNum
        self.fire.ClearBtnMap()
        self.Refresh()
        return True

    # ==========================
    # MIDI File Export / Import
    # ==========================

    def _GetSavePath(self):
        """Get the directory for saving MIDI files next to the script."""
        try:
            rootDir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if not os.path.isdir(rootDir):
                self.LastFileError = 'Invalid root path'
                return ''
            self.LastFileError = ''
            return rootDir
        except Exception as e:
            self.LastFileError = str(e)
            print('StepEdit SavePath error: ' + str(e))
            return ''

    def SaveMidiFile(self, slotName='pattern1'):
        """Export the internal grid as a Standard MIDI File (Format 0).
        Returns the file path or empty string on error."""
        try:
            self.LastFileError = ''
            saveDir = self._GetSavePath()
            if saveDir == '':
                return ''
            filePath = os.path.join(saveDir, slotName + '.mid')

            ppq = 96  # ticks per quarter note
            ticksPerStep = ppq // 4  # 16th note = 24 ticks

            # Collect all MIDI events
            events = []  # list of (absTick, status, data1, data2)
            for step in sorted(self.Grid.keys()):
                for pitch, noteData in self.Grid[step].items():
                    # Apply delay offset: delay 0-127, center=64 means no shift
                    delayOffset = int((noteData.delay - 64) * ticksPerStep / 128)
                    noteOnTick = max(0, step * ticksPerStep + delayOffset)
                    noteOffTick = noteOnTick + noteData.length * ticksPerStep
                    vel = max(1, min(127, noteData.velocity))
                    events.append((noteOnTick, 0x90, pitch, vel))      # note on
                    events.append((noteOffTick, 0x80, pitch, 0))       # note off

            # Sort by time, then note-off before note-on at same tick
            events.sort(key=lambda e: (e[0], 0 if e[1] == 0x80 else 1))

            # Build track data with delta times
            trackData = bytearray()

            # Tempo meta event: 120 BPM = 500000 microseconds/beat
            trackData += self._MidiVarLen(0)
            trackData += bytes([0xFF, 0x51, 0x03])
            trackData += struct.pack('>I', 500000)[1:]  # 3 bytes

            prevTick = 0
            for absTick, status, d1, d2 in events:
                delta = absTick - prevTick
                prevTick = absTick
                trackData += self._MidiVarLen(delta)
                trackData += bytes([status, d1, d2])

            # End of track
            trackData += self._MidiVarLen(0)
            trackData += bytes([0xFF, 0x2F, 0x00])

            # Write MIDI file
            with open(filePath, 'wb') as f:
                # Header: MThd, length=6, format=0, tracks=1, ppq
                f.write(b'MThd')
                f.write(struct.pack('>I', 6))
                f.write(struct.pack('>HHH', 0, 1, ppq))
                # Track: MTrk, length, data
                f.write(b'MTrk')
                f.write(struct.pack('>I', len(trackData)))
                f.write(trackData)

            self.LastFileError = ''
            return filePath
        except Exception as e:
            self.LastFileError = str(e)
            print('StepEdit SaveMidi error: ' + str(e))
            return ''

    def LoadMidiFile(self, slotName='pattern1'):
        """Import a Standard MIDI File into the internal grid.
        Returns True on success."""
        try:
            self.LastFileError = ''
            saveDir = self._GetSavePath()
            if saveDir == '':
                return False
            filePath = os.path.join(saveDir, slotName + '.mid')
            if not os.path.exists(filePath):
                self.LastFileError = 'No MIDI file'
                return False

            with open(filePath, 'rb') as f:
                data = f.read()

            # Parse header
            if data[0:4] != b'MThd':
                self.LastFileError = 'Invalid MIDI file'
                return False
            headerLen = struct.unpack('>I', data[4:8])[0]
            fmt, nTracks, ppq = struct.unpack('>HHH', data[8:14])
            ticksPerStep = ppq // 4
            if ticksPerStep <= 0:
                self.LastFileError = 'Invalid MIDI timing'
                return False

            # Find first track
            pos = 8 + headerLen
            if data[pos:pos+4] != b'MTrk':
                self.LastFileError = 'Missing MIDI track'
                return False
            trackLen = struct.unpack('>I', data[pos+4:pos+8])[0]
            trackStart = pos + 8
            trackEnd = trackStart + trackLen

            # Parse track events
            self.Grid.clear()
            absTick = 0
            i = trackStart
            activeNotes = {}  # pitch -> (onTick, step, velocity)
            maxStep = 0

            while i < trackEnd:
                # Read variable-length delta
                delta = 0
                while True:
                    b = data[i]
                    i += 1
                    delta = (delta << 7) | (b & 0x7F)
                    if b < 0x80:
                        break
                absTick += delta

                # Read event
                status = data[i]
                if status == 0xFF:  # meta event
                    i += 1
                    metaType = data[i]
                    i += 1
                    metaLen = 0
                    while True:
                        b = data[i]
                        i += 1
                        metaLen = (metaLen << 7) | (b & 0x7F)
                        if b < 0x80:
                            break
                    i += metaLen  # skip meta data
                    if metaType == 0x2F:  # end of track
                        break
                elif (status & 0xF0) == 0x90:  # note on
                    i += 1
                    pitch = data[i]; i += 1
                    vel = data[i]; i += 1
                    step = absTick // ticksPerStep
                    if vel > 0:
                        activeNotes[pitch] = (absTick, step, vel)
                        if step > maxStep:
                            maxStep = step
                    else:
                        # note on with vel 0 = note off
                        if pitch in activeNotes:
                            onTick, onStep, onVel = activeNotes[pitch]
                            lengthTicks = absTick - onTick
                            length = max(1, round(lengthTicks / ticksPerStep))
                            remainder = onTick - onStep * ticksPerStep
                            delay = 64 + int(remainder * 128 / ticksPerStep) if ticksPerStep > 0 else 64
                            delay = max(0, min(127, delay))
                            self.SetNote(onStep, pitch, onVel, length, delay)
                            del activeNotes[pitch]
                elif (status & 0xF0) == 0x80:  # note off
                    i += 1
                    pitch = data[i]; i += 1
                    i += 1  # skip velocity
                    if pitch in activeNotes:
                        onTick, onStep, onVel = activeNotes[pitch]
                        lengthTicks = absTick - onTick
                        length = max(1, round(lengthTicks / ticksPerStep))
                        remainder = onTick - onStep * ticksPerStep
                        delay = 64 + int(remainder * 128 / ticksPerStep) if ticksPerStep > 0 else 64
                        delay = max(0, min(127, delay))
                        self.SetNote(onStep, pitch, onVel, length, delay)
                        del activeNotes[pitch]
                else:
                    i += 1
                    if (status & 0xF0) not in [0xC0, 0xD0]:  # 2-byte events
                        i += 1  # 3-byte events
                    i += 1

            # Handle notes still active at end
            for pitch, (onTick, onStep, onVel) in activeNotes.items():
                length = max(1, (maxStep + 1) - onStep)
                remainder = onTick - onStep * ticksPerStep
                delay = 64 + int(remainder * 128 / ticksPerStep) if ticksPerStep > 0 else 64
                delay = max(0, min(127, delay))
                self.SetNote(onStep, pitch, onVel, length, delay)

            self.PatternLength = max(SE_DEFAULT_STEPS, maxStep + 1)
            self.LastFileError = ''
            return True
        except Exception as e:
            self.LastFileError = str(e)
            print('StepEdit LoadMidi error: ' + str(e))
            return False

    def SaveJsonFile(self, slotName='pattern1'):
        """Export the complete Fire state as a JSON file.
        Preserves all notes (chords), length, delay, mutes, mode.
        Returns file path or empty string on error."""
        try:
            self.LastFileError = ''
            saveDir = self._GetSavePath()
            if saveDir == '':
                return ''
            filePath = os.path.join(saveDir, slotName + '.json')

            notesList = []
            for step in sorted(self.Grid.keys()):
                for pitch, nd in self.Grid[step].items():
                    notesList.append({
                        'step': step,
                        'pitch': pitch,
                        'velocity': nd.velocity,
                        'length': nd.length,
                        'delay': nd.delay
                    })

            mutedSteps = [i for i in range(self.PatternLength) if self.StepMuted[i]]

            state = {
                'version': 1,
                'patternLength': self.PatternLength,
                'pitchOffset': self.PitchOffset,
                'stepOffset': self.StepOffset,
                'scaleIndex': self.ScaleIndex,
                'rootNote': self.RootNote,
                'chordMode': self.ChordMode,
                'autoChord': self.AutoChord,
                'mutedSteps': mutedSteps,
                'notes': notesList
            }

            with open(filePath, 'w') as f:
                json.dump(state, f, indent=2)

            self.LastFileError = ''
            return filePath
        except Exception as e:
            self.LastFileError = str(e)
            print('StepEdit SaveJson error: ' + str(e))
            return ''

    def LoadJsonFile(self, slotName='pattern1'):
        """Import a JSON state file into the internal grid.
        Restores all notes, length, delay, mutes, mode.
        Returns True on success."""
        try:
            self.LastFileError = ''
            saveDir = self._GetSavePath()
            if saveDir == '':
                return False
            filePath = os.path.join(saveDir, slotName + '.json')
            if not os.path.exists(filePath):
                self.LastFileError = 'No JSON file'
                return False

            with open(filePath, 'r') as f:
                state = json.load(f)

            self.Grid.clear()
            self.PatternLength = state.get('patternLength', SE_DEFAULT_STEPS)
            self.PitchOffset = state.get('pitchOffset', 48)
            self.StepOffset = state.get('stepOffset', 0)
            self.ScaleIndex = state.get('scaleIndex', -1)
            self.RootNote = state.get('rootNote', 0)
            self.ChordMode = state.get('chordMode', False)
            self.AutoChord = state.get('autoChord', False)
            if self.AutoChord:
                self.ChordMode = True

            self.StepMuted = [False] * SE_MAX_STEPS
            for ms in state.get('mutedSteps', []):
                if 0 <= ms < SE_MAX_STEPS:
                    self.StepMuted[ms] = True

            # Temporarily force chord mode to allow multiple notes per step
            oldChord = self.ChordMode
            self.ChordMode = True
            for n in state.get('notes', []):
                self.SetNote(
                    n['step'], n['pitch'],
                    n.get('velocity', SE_DEFAULT_VELOCITY),
                    n.get('length', SE_DEFAULT_LENGTH),
                    n.get('delay', SE_DEFAULT_DELAY)
                )
            self.ChordMode = oldChord

            self.LastFileError = ''
            return True
        except Exception as e:
            self.LastFileError = str(e)
            print('StepEdit LoadJson error: ' + str(e))
            return False

    @staticmethod
    def _MidiVarLen(value):
        """Encode an integer as MIDI variable-length quantity."""
        result = bytearray()
        result.append(value & 0x7F)
        value >>= 7
        while value > 0:
            result.append((value & 0x7F) | 0x80)
            value >>= 7
        result.reverse()
        return bytes(result)

    # ==========================
    # Coordinate Mapping
    # ==========================

    def PadToStepPitch(self, padNum):
        """Convert physical pad number to (step, pitch).

        Akai Fire turned 90° (USB port on top):
        - padNum layout: row * 16 + col (row 0-3, col 0-15)
        - Physical row (0-3) maps to step (bottom row = step 0 when vertical)
        - Physical col (0-15) maps to pitch (col 0 = lowest visible pitch)

        When turned 90° clockwise:
        - Physical bottom row (row 0) = leftmost column = earliest step
        - Physical col 0 = bottom = lowest pitch
        - Physical col 15 = top = highest pitch
        """
        phys_row = padNum // PadsStride   # 0-3
        phys_col = padNum % PadsStride    # 0-15

        step = self.StepOffset + phys_row
        pitch = self.PitchOffset + phys_col

        return step, pitch

    def StepPitchToPad(self, step, pitch):
        """Convert (step, pitch) to physical pad number, or -1 if not visible."""
        phys_row = step - self.StepOffset
        phys_col = pitch - self.PitchOffset

        if 0 <= phys_row < SE_VISIBLE_STEPS and 0 <= phys_col < SE_VISIBLE_PITCHES:
            return phys_row * PadsStride + phys_col
        return -1

    # ==========================
    # Scale Helpers
    # ==========================

    def IsNoteInScale(self, midiPitch):
        """Check if a MIDI pitch is in the current scale. Always True if chromatic."""
        if self.ScaleIndex < 0:
            return True  # chromatic = all notes in scale
        noteClass = (midiPitch - self.RootNote) % 12
        scaleNotes = self._GetScaleNotes()
        return noteClass in scaleNotes

    def IsRootNote(self, midiPitch):
        """Check if a MIDI pitch is the root note of the scale."""
        return (midiPitch % 12) == (self.RootNote % 12)

    def _GetScaleNotes(self):
        """Get the set of semitone offsets in the current scale."""
        if self.ScaleIndex < 0:
            return set(range(12))  # chromatic
        notes = set()
        for i in range(13):
            val = harmonicScales.HarmonicScaleList[self.ScaleIndex][i]
            if val == -1:
                break
            notes.add(val)
        return notes

    def GetScaleName(self):
        """Get the name of the current scale."""
        if self.ScaleIndex < 0:
            return 'Chromatic'
        return harmonicScales.HarmonicScaleNamesT[self.ScaleIndex]

    def CycleScale(self, direction):
        """Cycle through available scales. direction: +1 or -1."""
        if self.ScaleIndex < 0:
            if direction > 0:
                self.ScaleIndex = 0
            else:
                self.ScaleIndex = harmonicScales.HARMONICSCALE_LAST
        else:
            self.ScaleIndex += direction
            if self.ScaleIndex > harmonicScales.HARMONICSCALE_LAST:
                self.ScaleIndex = -1  # back to chromatic
            elif self.ScaleIndex < 0:
                self.ScaleIndex = -1  # chromatic

    # ==========================
    # Pad Colors
    # ==========================

    def _GetPadColor(self, step, pitch):
        """Determine the color for a pad at (step, pitch)."""
        inScale = self.IsNoteInScale(pitch)
        isRoot = self.IsRootNote(pitch)
        hasNote = self.HasNote(step, pitch)
        isMuted = self.StepMuted[step] if step < SE_MAX_STEPS else False
        isPlayhead = (step == self.CurrentStep)
        isSelected = (step, pitch) in self.SelectedPads

        # Priority: playing > selected/edit > note on > empty

        if isPlayhead and hasNote and not isMuted:
            return SE_COL_NOTE_PLAYING  # white flash for playing note

        if isSelected and self.EditMode:
            # will blink between SE_COL_NOTE_EDIT and note color (handled in Refresh with BlinkTimer)
            if self.fire.BlinkTimer < BlinkSpeed:
                return SE_COL_NOTE_EDIT
            else:
                if hasNote:
                    return SE_COL_NOTE_ON
                else:
                    return SE_COL_OFF

        if hasNote:
            if isMuted:
                return SE_COL_STEP_MUTED
            # color based on velocity (brighter = higher velocity)
            note = self.GetNote(step, pitch)
            if note is not None:
                intensity = max(0x20, int((note.velocity / 127.0) * 0xFF))
                return (0x00 << 16) | (intensity << 8) | 0x00  # green, brightness = velocity
            return SE_COL_NOTE_ON

        if isPlayhead:
            return SE_COL_PLAYHEAD  # dim playhead marker on empty pad

        if isMuted:
            return SE_COL_STEP_MUTED

        # Empty pad coloring based on scale
        if not inScale:
            return SE_COL_OUT_OF_SCALE
        if isRoot:
            return SE_COL_ROOT_NOTE
        # Black keys (sharps/flats) get a blue tint for visibility
        noteClass = pitch % 12
        if noteClass in (1, 3, 6, 8, 10):  # C#, D#, F#, G#, A#
            return SE_COL_BLACK_KEY
        return SE_COL_IN_SCALE

    # ==========================
    # Display / Refresh
    # ==========================

    def Refresh(self):
        """Refresh all 64 pads with the current grid state."""
        if not device.isAssigned():
            return

        dataOut = bytearray(0)

        for phys_row in range(SE_VISIBLE_STEPS):      # 0-3 (steps)
            for phys_col in range(SE_VISIBLE_PITCHES):  # 0-15 (pitches)
                padNum = phys_row * PadsStride + phys_col
                step = self.StepOffset + phys_row
                pitch = self.PitchOffset + phys_col

                color = self._GetPadColor(step, pitch)

                # Check if pad changed
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
            import screen
            screen.unBlank(True)
            self.fire.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)

        # Update mute/select buttons to show step mute state
        self._RefreshMuteButtons()

    def _RefreshMuteButtons(self):
        """Update the 4 mute buttons to reflect step mute state."""
        for i in range(SE_VISIBLE_STEPS):
            step = self.StepOffset + i
            muted = self.StepMuted[step] if step < SE_MAX_STEPS else False
            self.fire.SendCC(IDMute1 + i, SingleColorOff if muted else SingleColorFull)

    # ==========================
    # Pad Events (ON/OFF toggle)
    # ==========================

    def OnPadEvent(self, event, padNum):
        """Handle pad press/release.
        - Normal mode: toggle note ON/OFF
        - Edit mode: select/deselect pads for parameter editing
        """
        if event.midiId != MIDI_NOTEON:
            return  # ignore note off

        step, pitch = self.PadToStepPitch(padNum)

        if step < 0 or step >= SE_MAX_STEPS or pitch < 0 or pitch > 127:
            return

        if not self.EditMode:
            # Normal mode: toggle note (with chord support)
            general.saveUndo('Fire: StepEdit note', UF_PR, False)

            # Determine which pitches to toggle (chord or single)
            chordIntervals = self._GetActiveChordIntervals()
            pitches = [pitch + iv for iv in chordIntervals if 0 <= pitch + iv <= 127]

            # Check if root note exists to decide add vs remove
            hasRoot = self.HasNote(step, pitch)

            if hasRoot:
                # Remove all chord notes at this step
                for p in pitches:
                    self.RemoveNote(step, p)
            else:
                # Add all chord notes at this step
                for p in pitches:
                    self.SetNote(step, p)

            self._SyncStepToFL(step)
            if not hasRoot:
                # Preview the chord
                chanIndex = channels.selectedChannel(1)
                if chanIndex >= 0:
                    for p in pitches:
                        channels.midiNoteOn(chanIndex, p, SE_DEFAULT_VELOCITY)
                    for p in pitches:
                        channels.midiNoteOn(chanIndex, p, 0)
            self.Refresh()
        else:
            # Edit mode: toggle pad selection
            # In AutoChord mode, select/deselect ALL notes at this step together
            # In Poly manuel or Mono, select note by note
            key = (step, pitch)
            if key in self.SelectedPads:
                # Deselect
                if self.AutoChord:
                    self.SelectedPads = [(s, p) for s, p in self.SelectedPads if s != step]
                else:
                    self.SelectedPads.remove(key)
            else:
                if self.HasNote(step, pitch):
                    if self.AutoChord:
                        # Select all notes at this step (chord group)
                        notes = self.GetNotesAtStep(step)
                        for p in notes.keys():
                            if (step, p) not in self.SelectedPads:
                                self.SelectedPads.append((step, p))
                    else:
                        self.SelectedPads.append(key)
            self.Refresh()

    # ==========================
    # Edit Mode
    # ==========================

    def ToggleEditMode(self):
        """Toggle edit mode ON/OFF. Returns new state."""
        self.EditMode = not self.EditMode
        if not self.EditMode:
            self.SelectedPads.clear()
        return self.EditMode

    def OnKnobEdit(self, knobId, increment):
        """Handle knob turn in edit mode. Modifies selected notes.

        Knob mapping:
        - Knob 1: Pitch transpose (all selected notes move together)
        - Knob 2: Velocity
        - Knob 3: Note Length (in steps)
        - Knob 4: Time Delay (offset within step)
        """
        if not self.EditMode or len(self.SelectedPads) == 0:
            return ''  # no feedback text

        if knobId == IDKnob1:
            return self._EditPitch(increment)
        elif knobId == IDKnob2:
            return self._EditVelocity(increment)
        elif knobId == IDKnob3:
            return self._EditLength(increment)
        elif knobId == IDKnob4:
            return self._EditDelay(increment)
        return ''

    def _EditPitch(self, increment):
        """Transpose all selected notes by increment semitones."""
        # Check if transpose would go out of range
        for step, pitch in self.SelectedPads:
            newPitch = pitch + increment
            if newPitch < 0 or newPitch > 127:
                return 'Out of range'

        general.saveUndo('Fire: StepEdit pitch', UF_PR, True)

        # Move all notes
        notesToMove = []
        for step, pitch in self.SelectedPads:
            note = self.GetNote(step, pitch)
            if note is not None:
                notesToMove.append((step, pitch, note.velocity, note.length, note.delay))

        # Remove old notes
        for step, pitch, vel, length, delay in notesToMove:
            self.RemoveNote(step, pitch)

        # Add at new positions and sync to FL
        affectedSteps = set()
        newSelected = []
        for step, pitch, vel, length, delay in notesToMove:
            newPitch = pitch + increment
            self.SetNote(step, newPitch, vel, length, delay)
            newSelected.append((step, newPitch))
            affectedSteps.add(step)

        for s in affectedSteps:
            self._SyncStepToFL(s)

        self.SelectedPads = newSelected

        # Adjust view if needed
        if len(newSelected) > 0:
            minPitch = min(p for _, p in newSelected)
            maxPitch = max(p for _, p in newSelected)
            if minPitch < self.PitchOffset:
                self.PitchOffset = minPitch
            elif maxPitch >= self.PitchOffset + SE_VISIBLE_PITCHES:
                self.PitchOffset = maxPitch - SE_VISIBLE_PITCHES + 1
            self.fire.ClearBtnMap()

        self.Refresh()
        self._UpdateFLView()
        pitchName = utils.GetNoteName(newSelected[0][1]) if len(newSelected) > 0 else ''
        return 'Pitch: ' + pitchName

    def _EditVelocity(self, increment):
        """Change velocity of all selected notes."""
        affectedSteps = set()
        for step, pitch in self.SelectedPads:
            note = self.GetNote(step, pitch)
            if note is not None:
                note.velocity = max(1, min(127, note.velocity + increment * 4))
                affectedSteps.add(step)

        for s in affectedSteps:
            self._SyncStepToFL(s)

        self.Refresh()
        # Show velocity of first selected note
        if len(self.SelectedPads) > 0:
            note = self.GetNote(self.SelectedPads[0][0], self.SelectedPads[0][1])
            if note is not None:
                return 'Velocity: ' + str(note.velocity)
        return 'Velocity'

    def _EditLength(self, increment):
        """Change length (in steps) of all selected notes."""
        for step, pitch in self.SelectedPads:
            note = self.GetNote(step, pitch)
            if note is not None:
                note.length = max(1, min(SE_DEFAULT_STEPS, note.length + increment))

        self.Refresh()
        if len(self.SelectedPads) > 0:
            note = self.GetNote(self.SelectedPads[0][0], self.SelectedPads[0][1])
            if note is not None:
                return 'Length: ' + str(note.length) + ' steps'
        return 'Length'

    def _EditDelay(self, increment):
        """Change time delay (offset) of all selected notes."""
        for step, pitch in self.SelectedPads:
            note = self.GetNote(step, pitch)
            if note is not None:
                note.delay = max(0, min(127, note.delay + increment * 4))

        self.Refresh()
        if len(self.SelectedPads) > 0:
            note = self.GetNote(self.SelectedPads[0][0], self.SelectedPads[0][1])
            if note is not None:
                return 'Delay: ' + str(note.delay)
        return 'Delay'

    # ==========================
    # Step Mute
    # ==========================

    def ToggleStepMute(self, muteIndex):
        """Toggle mute for the step at muteIndex (0-3 visible). Returns display text.
        Writes gridBit to FL: 0 when muted, 1 when unmuted (so FL stops/resumes playing).
        On unmute, restores full note data (pitch, velocity, length) to FL.
        Internal engine also checks StepMuted for poly extra notes."""
        step = self.StepOffset + muteIndex
        if step < SE_MAX_STEPS:
            self.StepMuted[step] = not self.StepMuted[step]
            chanIndex = channels.selectedChannel(1)
            if chanIndex >= 0:
                try:
                    if self.StepMuted[step]:
                        channels.setGridBit(chanIndex, step, 0)
                    else:
                        self._WriteStepToFL(chanIndex, step)
                except Exception as e:
                    print('StepEdit ToggleStepMute FL sync error: ' + str(e))
            self.Refresh()
            if self.StepMuted[step]:
                return 'Step ' + str(step + 1) + ' muted'
            else:
                return 'Step ' + str(step + 1) + ' unmuted'
        return ''

    # ==========================
    # FL Studio View Tracking
    # ==========================

    def _ShowChannelRackRect(self):
        """Show red selection rectangle in channel rack for the visible steps.
        ui.crDisplayRect takes (left, top, WIDTH, HEIGHT, duration) not absolute coords.
        In multi-device mode, shows combined rect across all synced devices."""
        chanIndex = channels.channelNumber()
        if chanIndex < 0:
            return
        try:
            if ui.getVisible(widChannelRack):
                devCount = self._GetSyncDeviceCount()
                if devCount > 1:
                    baseStep = self.StepOffset - self.fire.StepEditDeviceIndex * SE_VISIBLE_STEPS
                    baseStep = max(0, baseStep)
                    width = SE_VISIBLE_STEPS * devCount
                else:
                    baseStep = self.StepOffset
                    width = SE_VISIBLE_STEPS
                ui.crDisplayRect(baseStep, chanIndex, width, 1, 60000)
        except Exception:
            pass

    def _UpdatePianoRollView(self):
        """Scroll FL Studio's piano roll vertically to follow pitch changes.
        ui.up()/ui.down() scrolls ~3 semitones per call, so we accumulate
        pitch delta and only fire a scroll every 3 semitones."""
        try:
            if not ui.getVisible(widPianoRoll):
                return
            if not ui.getFocused(widPianoRoll):
                return
        except Exception:
            return

        prevPitch = getattr(self, '_prevViewPitch', self.PitchOffset)
        self._prevViewPitch = self.PitchOffset

        try:
            pitchDelta = self.PitchOffset - prevPitch
            self._prScrollAccum += pitchDelta
            scrollCalls = self._prScrollAccum // 3
            if scrollCalls > 0:
                for _ in range(min(scrollCalls, 6)):
                    ui.up()
                self._prScrollAccum -= scrollCalls * 3
            elif scrollCalls < 0:
                for _ in range(min(abs(scrollCalls), 6)):
                    ui.down()
                self._prScrollAccum -= scrollCalls * 3
        except Exception:
            pass

    def _UpdateFLView(self):
        """Update both channel rack rectangle and piano roll view."""
        self._ShowChannelRackRect()
        self._UpdatePianoRollView()

    # ==========================
    # Navigation
    # ==========================

    def _GetStepRangeText(self):
        """Return OLED text showing step range. In multi-device mode, shows the
        combined range across all devices (e.g. 'Steps 1-8' with 2 devices)."""
        devCount = self._GetSyncDeviceCount()
        if devCount > 1:
            # Show combined range: base (removing this device's offset) to base + total
            baseStep = self.StepOffset - self.fire.StepEditDeviceIndex * SE_VISIBLE_STEPS
            baseStep = max(0, baseStep)
            totalSteps = SE_VISIBLE_STEPS * devCount
            return 'Steps ' + str(baseStep + 1) + '-' + str(baseStep + totalSteps)
        return 'Steps ' + str(self.StepOffset + 1) + '-' + str(self.StepOffset + SE_VISIBLE_STEPS)

    def _GetSyncDeviceCount(self):
        """Return the total number of synced devices for step edit scroll multiplier.
        Single=1, Master=1+slaves, Slave=2 (assumes at least master+self)."""
        if self.fire.MultiDeviceMode == MultiDev_Master:
            return 1 + max(1, len(self.fire.SlavedDevices))
        elif self.fire.MultiDeviceMode == MultiDev_Slave:
            return 2  # at least master + self
        return 1

    def ScrollSteps(self, direction):
        """Scroll steps by N*4 where N=number of synced devices. direction: +1 or -1."""
        devCount = self._GetSyncDeviceCount()
        stepAmount = SE_VISIBLE_STEPS * devCount
        newOfs = self.StepOffset + direction * stepAmount
        if newOfs < 0:
            newOfs = 0
        if newOfs >= self.PatternLength:
            newOfs = max(0, self.PatternLength - SE_VISIBLE_STEPS)
        self.StepOffset = newOfs
        self.fire.ClearBtnMap()
        self.Refresh()
        self._UpdateFLView()
        self._DispatchStepEditSync()
        return self._GetStepRangeText()

    def ScrollStepsSingle(self, direction):
        """Scroll steps by 1 per synced device. direction: +1 or -1."""
        stepAmount = self._GetSyncDeviceCount()
        newOfs = self.StepOffset + direction * stepAmount
        if newOfs < 0:
            newOfs = 0
        if newOfs >= self.PatternLength:
            newOfs = max(0, self.PatternLength - SE_VISIBLE_STEPS)
        self.StepOffset = newOfs
        self.fire.ClearBtnMap()
        self.Refresh()
        self._UpdateFLView()
        self._DispatchStepEditSync()
        return self._GetStepRangeText()

    def ScrollPitch(self, direction, semitones=1):
        """Scroll visible pitch range. direction: +1 (up) or -1 (down). semitones: amount to scroll."""
        newOfs = self.PitchOffset + direction * semitones
        if newOfs < 0:
            newOfs = 0
        if newOfs + SE_VISIBLE_PITCHES > 128:
            newOfs = 128 - SE_VISIBLE_PITCHES
        if newOfs == self.PitchOffset:
            return ''  # no change
        self.PitchOffset = newOfs
        self.fire.ClearBtnMap()
        self.Refresh()
        self._UpdateFLView()
        self._DispatchStepEditSync()
        lowName = utils.GetNoteName(self.PitchOffset)
        highName = utils.GetNoteName(self.PitchOffset + SE_VISIBLE_PITCHES - 1)
        return lowName + ' - ' + highName

    # ==========================
    # Playback Engine
    # ==========================

    def OnUpdateBeatIndicator(self, beat):
        """Called by FL Studio on beat updates. Advances the playhead."""
        # beat: 0 = bar, 1 = beat, 2 = step (16th note)
        # We don't directly use this for precise stepping,
        # but it triggers our refresh to show the playhead
        pass

    def _GetTicksPerStep(self):
        """Get ticks per step (16th note) from FL Studio PPQ."""
        ppq = general.getRecPPQ()
        if ppq <= 0:
            ppq = 96
        return max(1, ppq // 4)

    def _DelayToTickOffset(self, delay, ticksPerStep):
        """Convert internal delay (0-127, center=64) to signed tick offset.
        delay=0 -> -ticksPerStep//2, delay=64 -> 0, delay=127 -> +ticksPerStep//2"""
        if delay == 64 or delay == SE_DEFAULT_DELAY:
            return 0
        return int((delay - 64) * ticksPerStep / 128)

    def ApplyMultiDeviceOffset(self):
        """Apply device index offset to StepOffset. Called from device_Fire.py
        when this device becomes a slave while already in Step Edit mode."""
        newOffset = max(0, self.fire.StepEditDeviceIndex * SE_VISIBLE_STEPS)
        if newOffset != self.StepOffset:
            self.StepOffset = newOffset
            self.fire.ClearBtnMap()
            self.Refresh()
        self._ShowChannelRackRect()
        self._DispatchStepEditSync()

    def OnIdle(self):
        """Called periodically. Handles playback sync with FL Studio transport.
        FL grid bits are NEVER cleared — notes always remain visible in channel rack.
        In Mono mode: FL plays via gridBits, internal engine does nothing.
        In Poly/Accord mode: FL plays the lowest note, internal engine plays extra notes."""
        # Keep channel rack rectangle visible - throttled to every 2 seconds
        now = time.time()
        if now - getattr(self, '_lastRectTime', 0) > 2.0:
            self._ShowChannelRackRect()
            self._lastRectTime = now

        isPlaying = transport.isPlaying()
        self._wasPlaying = isPlaying

        if not isPlaying:
            if self.CurrentStep != -1:
                self._StopAllPlayingNotes()
                self.CurrentStep = -1
                self.LastPlayedStep = -1
                self.LastProcessedTick = -1
                self.PendingNotes.clear()
                self.Refresh()
            return

        songPos = transport.getSongPos(SONGLENGTH_ABSTICKS)
        if songPos < 0:
            return

        ticksPerStep = self._GetTicksPerStep()
        patternTicks = self.PatternLength * ticksPerStep
        if patternTicks <= 0:
            return

        currentTick = int(songPos) % patternTicks
        currentStep = currentTick // ticksPerStep

        # --- Process pending note-ons (delayed notes) ---
        stillPending = []
        for onTick, chanIdx, pitch, vel, offTick in self.PendingNotes:
            if currentTick >= onTick:
                channels.midiNoteOn(chanIdx, pitch, vel)
                self.ActiveNotes.append((chanIdx, pitch, offTick))
            else:
                stillPending.append((onTick, chanIdx, pitch, vel, offTick))
        self.PendingNotes = stillPending

        # --- Process note-offs for expired active notes ---
        stillActive = []
        for chanIdx, pitch, offTick in self.ActiveNotes:
            if currentTick >= offTick:
                channels.midiNoteOn(chanIdx, pitch, 0)
            else:
                stillActive.append((chanIdx, pitch, offTick))
        self.ActiveNotes = stillActive

        # --- Schedule new notes when entering a new step ---
        if currentStep != self.LastPlayedStep:
            self.LastPlayedStep = currentStep
            self.CurrentStep = currentStep

            if not self.StepMuted[currentStep]:
                self._ScheduleNotesAtStep(currentStep, currentTick, ticksPerStep, patternTicks)

            self.Refresh()

    def _ScheduleNotesAtStep(self, step, currentTick, ticksPerStep, patternTicks):
        """Schedule note-on/off for all notes at the given step.
        In Mono mode: do nothing — FL plays the note via gridBits.
        In Poly/Accord mode: play only the EXTRA notes (not the lowest,
        which FL already plays via gridBits)."""
        if not self.ChordMode:
            # Mono: FL handles playback entirely via gridBits
            return

        chanIndex = channels.selectedChannel(1)
        if chanIndex < 0:
            return

        notes = self.GetNotesAtStep(step)
        if len(notes) <= 1:
            # Only one note (or none) — FL handles it
            return

        # Find the lowest pitch (FL plays this one via gridBit)
        lowestPitch = min(notes.keys())

        for pitch, noteData in notes.items():
            if pitch == lowestPitch:
                continue  # FL plays the lowest note
            if noteData.velocity <= 0:
                continue

            delayOffset = self._DelayToTickOffset(noteData.delay, ticksPerStep)
            onTick = (step * ticksPerStep + delayOffset) % patternTicks
            offTick = (onTick + noteData.length * ticksPerStep) % patternTicks

            # If delay makes onTick in the past (within this step), play immediately
            if delayOffset <= 0:
                channels.midiNoteOn(chanIndex, pitch, noteData.velocity)
                self.ActiveNotes.append((chanIndex, pitch, offTick))
            else:
                # Schedule for later in this step
                self.PendingNotes.append((onTick, chanIndex, pitch, noteData.velocity, offTick))

    def _StopAllPlayingNotes(self):
        """Send note-off for all currently playing and pending notes."""
        for chanIdx, pitch, offTick in self.ActiveNotes:
            channels.midiNoteOn(chanIdx, pitch, 0)
        self.ActiveNotes.clear()
        for onTick, chanIdx, pitch, vel, offTick in self.PendingNotes:
            pass  # never triggered, just discard
        self.PendingNotes.clear()
        # Legacy compat
        for chanIndex, pitch in self.PlayingNotes:
            channels.midiNoteOn(chanIndex, pitch, 0)
        self.PlayingNotes.clear()

    # ==========================
    # Mode Activation
    # ==========================

    def OnActivate(self):
        """Called when Step Edit mode becomes active.
        Reads FL channel rack into internal grid.
        FL grid bits are NEVER cleared — FL always plays via gridBits.
        Internal engine only adds extra poly notes."""
        self.fire.ClearBtnMap()
        self.SelectedPads.clear()
        self.EditMode = False
        self._wasPlaying = transport.isPlaying()
        # In multi-device mode, apply device index offset so each device shows different steps
        if self.fire.MultiDeviceMode != MultiDev_Single:
            self.StepOffset = max(0, self.fire.StepEditDeviceIndex * SE_VISIBLE_STEPS)
        if not self.ChordMode:
            self.SyncFromChannelRackMono(True)
        self.Refresh()
        self._UpdateFLView()
        self._DispatchStepEditSync()

    def OnDeactivate(self):
        """Called when leaving Step Edit mode.
        Restores FL grid bits from internal grid so FL step sequencer works again."""
        self._StopAllPlayingNotes()
        self.SelectedPads.clear()
        self.EditMode = False
        # Restore FL grid from internal state
        self.SyncAllToFL()

    # ==========================
    # Multi-Device Step Edit Sync
    # ==========================

    def _DispatchStepEditSync(self):
        """Broadcast current step/pitch offsets to other Fire devices.
        Only sends if multi-device mode is active.
        Sends the BASE step offset (this device's offset minus its own device index shift)."""
        if self.fire.MultiDeviceMode == MultiDev_Single:
            return
        try:
            # Compute base step offset: remove this device's index shift
            baseStep = self.StepOffset - self.fire.StepEditDeviceIndex * SE_VISIBLE_STEPS
            baseStep = max(0, baseStep)
            # Pack: data1 = baseStep + 128 (to allow negatives), data2 = PitchOffset, data3 = 0
            self.fire.DispatchMessageToDeviceScripts(SM_StepEditSync, baseStep + 128, self.PitchOffset, 0)
        except Exception as e:
            print('StepEdit sync dispatch error: ' + str(e))

    def OnStepEditSync(self, baseStepOffset, pitchOffset):
        """Receive step edit sync from another device.
        Apply the base offset + this device's index shift.
        Called from device_Fire.py when SM_StepEditSync is received."""
        newStep = baseStepOffset + self.fire.StepEditDeviceIndex * SE_VISIBLE_STEPS
        newStep = max(0, min(newStep, max(0, self.PatternLength - SE_VISIBLE_STEPS)))
        newPitch = max(0, min(pitchOffset, 128 - SE_VISIBLE_PITCHES))
        changed = (newStep != self.StepOffset) or (newPitch != self.PitchOffset)
        if changed:
            self.StepOffset = newStep
            self.PitchOffset = newPitch
            self.fire.ClearBtnMap()
            self.Refresh()
            self._UpdateFLView()

    # ==========================
    # OLED Display
    # ==========================

    def GetDisplayText(self):
        """Get persistent top line text for the OLED display."""
        chanIndex = channels.selectedChannel(1)
        chanName = ''
        if chanIndex >= 0:
            chanName = channels.getChannelName(chanIndex)

        stepRange = self._GetStepRangeText()
        lowNote = utils.GetNoteName(self.PitchOffset)
        highNote = utils.GetNoteName(self.PitchOffset + SE_VISIBLE_PITCHES - 1)
        modeName = 'CHORD' if self.ChordMode else 'MONO'

        if self.EditMode:
            line1 = '[EDIT ' + modeName + '] ' + chanName
        else:
            line1 = 'StepEdit ' + modeName + ': ' + chanName
        line2 = stepRange + ' ' + lowNote + '-' + highNote
        return line1, line2

