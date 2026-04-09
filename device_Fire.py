#   name=Akai Fire EndGAme
# url=https://forum.image-line.com/viewtopic.php?p=1496543#p1496543
# receiveFrom=Akai Fire EndGAme
# version 2026.2 - Modularisé

import patterns
import channels
import mixer
import device
import transport
import arrangement
import general
import launchMapPages
import playlist
import ui
import screen
import plugins

from midi import *
import utils
import time
import harmonicScales

# --- Import des modules Fire ---
from fire_modules.constants import *
from fire_modules.fire_utils import TAccentModeParams, TiniKeyRecord, TiniKeySection, TMidiEvent
from fire_modules.display import DisplayManager
from fire_modules.note_mode import NoteMode
from fire_modules.step_seq import StepSeqMode
from fire_modules.drum_mode import DrumMode
from fire_modules.fl_control_mode import FLControlMode
from fire_modules.perf_mode import PerfMode
from fire_modules.step_edit_mode import StepEditMode
from fire_modules.chord_select_mode import ChordSelectMode


class TFire():
    def __init__(self):
        self.ChanRackOfs = 0
        self.ChanRackStartPos = 0
        self.TrackOfs = 0
        self.ClipOfs = 0
        self.BtnT = bytearray(IdxButtonLast) # see buttons indexes above
        self.BtnLastClip = [0 for x in range(PadsH * PadsW)]
        for n in range(0, len(self.BtnLastClip)):
            self.BtnLastClip[n] = utils.TClipLauncherLastClip(MaxInt, MaxInt, MaxInt)
        self.BtnMap = [0] * 64
        self.PlayingNotes = bytearray(0)
        self.PlayingChannels = [] # for "omni" drum mode
        self.CurStep = 0 # current playing step when FL plays
        self.MuteBtnStates = [False] * 4 # to know if mute buttons are held
        self.DidTweakLooping = False
        self.CurrentNoteGrid = [[0 for x in range(PadsH)] for y in range(PadsW)]
        self.SlavedDevices = {}   # port -> mode layout
        self.MultiDeviceMode = MultiDev_Single
        self.SlaveModeLayout = 0 # see SlaveModeLayout_ constants
        self.StepEditDeviceIndex = 0  # 0=master/first, 1=second, 2=third, 3=fourth device for step edit sync
        
        self.SlaveLayoutSelectionMode = False # when True, shows a menu to select the slave layout
        self.AnalyzerMode = 0
        self.AnalyzerChannel = 0
        self.AnalyzerFlipX = False
        self.analyzerFlipY = False
        self.AnalyzerScrollX  = False
        self.AnalyzerScrollY = False
        self.CurrentMode = 0
        self.NonVisMode = 0
        self.OldMode = 0
        self.OldMode = 0 # see mode constants
        self.AccentMode = False # True when "accent" is enabled in step seq mode
        self.AccentParams = TAccentModeParams(0, 0, 0, 0, 0) # default param values of steps in accent mode
        self.OverviewMode = False # True when in "overview" in perf mode
        self.ModeBeforeChordSelect = ModeStepEdit  # saved mode to return to when toggling ChordSelect off
        self.BrowserMode = False # True when "browser" is enabled
        self.BrowserShouldClose = False
        self.BrowserShouldAutoHide = False # to restore the state of the browser when exiting browser mode
        self.JogWheelPushed = False # True when holding down the jogwheel
        self.JogWheelHeldTime = 0.0 # time (number of idle calls) during which the Jog button was held
        self.GridBtnHeldTime = 0 # time (number of idle calls) during which the grid buttons were held
        self.GridBtnHeldTriggerTime = 0 # time before it retriggers the same action (reduces the more you hold)
        self.GridUpBtnHeld = False
        self.GridDownBtnHeld = False # True if either grid buttons are pressed
        self.PatBtnHeldTime = 0 # time (number of idle calls) during which the pattern up | down button was held
        self.PatUpBtnHeld = False
        self.PatDownBtnHeld = False # True if either (or both) pat up | pat down buttons are held
        self.PatBtnHeldTriggerTime = 0 # time before it retriggers the same action (reduces the more you hold)
        self.CurrentKnobsMode = 0 # active mode for knobs (CR, mixer, user1, user2)
        self.CurrentMixerTrack = 0 # mixer track being tweaked by the knobs
        self.CurrentNoteMode = 0
        self.OldNoteMode = 0 # for notes mode (dual keyboards | scales)
        self.CurrentDrumMode = 0 # for drum mode (FPC, Slicex, etc)
        self.TopText = '' # text at the top of the screen
        self.DisplayedText = '' # central text (bigger)
        self.KeyOffset = 36 # for notes mode
        self.TextTimer = 0 # to make the text disappear after a while
        self.TopTextTimer = 0.0
        self.DisplayZoneTimer = 0 # to make the self.Display zone disappearing after using the jog
        self.BlinkTimer = 0 # to make buttons blink
        self.TrackSelIdleValue = 0 # for the idle anim of the track selectors (when "receive notes from" is active)
        self.HeldPadsChanged = False # True when held pads were tweaked via knobs/jogwheel (to avoid switching their state after changing a param)
        self.ShiftHeld = False
        self.AltHeld = False # True when holding shift | alt buttons
        self.LayoutSelectionMode = False # True when selection the layout in notes mode
        self.MixerTrackSelectionMode = False # True when assigning a channel's mixer track
        self.TouchingKnob = False # Is the user currently handling a knob?
        self.KnobTouched = 0 # The knob the user is currently touching
        self.UHP = 0
        self.UHC = 0
        self.UHL = 0 # Stored history (undo) positions
        self.ChangeFlag = False # Set if the user changes a step parameter
        self.MasterDeviceChanRackOfs = 0
        self.MasterDeviceChanRackStartPos = 0
        self.MasterDeviceClipOfs = 0
        self.MasterTrackOfs = 0
        self.MasterClipOfs = 0

        self.bmpTimer = 0 #TDateTime
        self.NoteColorSet = 0
        self.LastRawData1 = 0
        self.LastRawData2 = 0

        self.LastIdleSec = 0
        self.IdleFPS = 0
        self.ScreenMode = ScreenModeNone
        self.KnobsV = [0] * 4
        self.HeldPads = bytearray(0)
        self.PlayingPads = []

        #todo def GetEventForPad(Device: TMIDIInDevice_Fire PadNum): pRecEvent
        #todo def GetTimeForPad(Device: TMIDIInDevice_Fire PadNum):
        self.KeyColorsDefault = [[0xFF4000, 0xFFFFFF, 0x0F0F0F, 0x7F7F7F, 0x9CFF00, 0x00FF00, 0x80FF00, 0xFFFF00, 0xFF4000, 0x000080, 0x0060FF, 0x000080],  [0x00FFFF, 0xFFFFFF, 0x0F0F0F, 0x7F7F7F, 0xFF4000, 0x00FFFF, 0x7FFFFF, 0xFFFFFF, 0xFF0000, 0x000080, 0x0060FF, 0x000080]]
        self.KeyColors = [[0 for x in range(7 + PadsH + 1)] for y in range(2)]
        self.FLFirePadBrightness = 0
        self.FLFirePadSaturation = 0

        self.FLFireDeviceCount = 0
        self.IdleDeviceCount = 0
        self.AnalyzerHue = 0.0

        # --- Initialisation des modules ---
        self.display_mgr = DisplayManager(self)
        self.note_mode_handler = NoteMode(self)
        self.step_seq_handler = StepSeqMode(self)
        self.drum_mode_handler = DrumMode(self)
        self.fl_control_handler = FLControlMode(self)
        self.perf_mode_handler = PerfMode(self)
        self.step_edit_handler = StepEditMode(self)
        self.chord_select_handler = ChordSelectMode(self)

    def LoadKeyColors(self):
        for n in range(0, 2):
            for i in range(0, 7 + PadsH + 1):
                self.KeyColors[n][i] = self.KeyColorsDefault[n][i]

    def OnInit(self):

        self.FLFireDeviceCount += 1
        if self.FLFireDeviceCount == 1: # first (or only) FL Fire unit. Load the settings
            self.LoadKeyColors()
            self.FLFirePadBrightness = 96
            self.FLFirePadSaturation = 101
            self.FromToReg(False)

        self.ScreenMode = ScreenModeNone
        self.CurStep = -1
        self.ChanRackOfs = 0
        self.ChanRackStartPos = 0
        self.TrackOfs = 0
        self.ClipOfs = 0
        self.KeyOffset = 36
        self.CurrentMode = ModeStepSeq
        self.OldMode = 128 # make sure it's invalid not to miss the first update
        self.CurrentKnobsMode = KnobsModeChannelRack
        self.CurrentNoteMode = NoteModeDualKeyb
        self.OldNoteMode = -1
        self.CurrentDrumMode = DrumModeFPC
        self.TopText = 'FL Studio'
        self.DisplayedText = ''
        self.ShiftHeld = False
        self.AltHeld = False
        self.OverviewMode = False
        self.JogWheelPushed = False
        self.JogWheelHeldTime = 0
        self.BrowserMode = False
        self.BrowserShouldClose = False
        self.BrowserShouldAutoHide = False
        self.TextTimer = 0
        self.TopTextTimer = 0.0
        self.DisplayZoneTimer = 0
        self.BlinkTimer = 0
        self.HeldPadsChanged = False
        self.TrackSelIdleValue = 0
        self.CurrentMixerTrack = 0
        self.MultiDeviceMode = MultiDev_Single
        self.SlaveModeLayout = SlaveModeLayout_Right # to the right by default
        self.MasterDevice = 0
        self.SlavedDevices = {}
        self.TouchingKnob = False
        self.KnobTouched = 0
        self.PatBtnHeldTime = 0
        self.PatUpBtnHeld = False
        self.PatDownBtnHeld = False
        self.PatBtnHeldTriggerTime = HeldButtonRetriggerTime
        self.GridBtnHeldTime = 0
        self.GridUpBtnHeld = False
        self.GridDownBtnHeld = False
        self.GridBtnHeldTriggerTime = HeldButtonRetriggerTime // 2
        for n in range(0, 4):
            self.MuteBtnStates[n] = False
        self.DidTweakLooping = False
        self.AccentParams = TAccentModeParams(DotNote_Default, 100, 64, 127, 0)
        self.DisplayWidth = 128
        self.DisplayHeight = 64

        for n in range(0, len(self.BtnT)):
            self.BtnT[n] = 0
        self.ClearBtnMap()
        self.ClearAllButtons()
        launchMapPages.createOverlayMap(1, 8, PadsW, PadsH)
        for y in range(0, PadsH):
            for x in range(0, PadsW):
                launchMapPages.setMapItemTarget(-1, y * PadsW + x, y * PadsStride + x)

        self.display_mgr.InitScreen()

        self.bmpTimer = time.time()
        self.Reset()
        self.SetOfs(self.TrackOfs, self.ClipOfs)
        self.ClearDisplay()

    def OnDeInit(self):

        if self.FLFireDeviceCount == 1: # last (or only) FL Fire unit. Save the settings
            self.FromToReg(True)

        self.Reset()
        self.display_mgr.DeInitScreen()
        self.FLFireDeviceCount -= 1

    def CutPlayingNotes(self):

        if (len(self.PlayingNotes) == 0) & (len(self.PlayingChannels) == 0):
            return
        #for n in range(0, len(self.PlayingChannels)):
        #    if utils.InterNoSwap(self.PlayingChannels[n], 0, channels.channelCount()):
        #        channels.midiNoteOn(self.PlayingChannels[n], DotNote_Default, -127)
        self.PlayingChannels = []
        chanNum = self.IsLockedByReceiveNotesFrom()
        if chanNum < 0:
            chanNum = channels.channelNumber()
        if chanNum < 0:
            return

        #for n in range(0, len(self.PlayingNotes)):
        #    channels.midiNoteOn(chanNum, self.PlayingNotes[n], -127) # negative vel for note off
        self.PlayingNotes = bytearray(0)

    def Reset(self):

        try:
            self.step_edit_handler._StopAllPlayingNotes()
        except Exception:
            pass
        self.ClearAllPads()
        self.CurStep = -1
        self.ClearAllButtons()
        self.ClearDisplay()
        self.ClearBtnMap()
        self.ClearKnobsMode()
        self.PlayingNotes = bytearray(0)
        self.PlayingChannels = []

    def FromToReg(self, ToReg):
        return
        #todo IntegerFromToReg(['PadBrightness', 'PadSaturation'], [@self.FLFirePadBrightness, @self.FLFirePadSaturation], FIniFile, Ini_Devices + '\' + FLFireDeviceName, ToReg)

    def Sign(self, AValue):
      Result = 0
      if AValue < 0:
        Result = -1
      elif AValue > 0:
        Result = 1
      return Result

    def DisplayText(self, Font, Justification, PageTop, Text, CheckIfSame, DisplayTime = 0):
        self.display_mgr.DisplayText(Font, Justification, PageTop, Text, CheckIfSame, DisplayTime)

    def DisplayBar(self, Text, Value, Bipolar):
        self.display_mgr.DisplayBar(Text, Value, Bipolar)

    def DisplayTimedText(self, Text):
        self.display_mgr.DisplayTimedText(Text)

    def OnDisplayZone(self):

        if self.MultiDeviceMode == MultiDev_Slave:
          self.DispatchMessageToDeviceScripts(SM_SlaveUpdateDisplayZone, 0, 0, 0)
        else:
          self.perf_mode_handler.OnDisplayZone()

    def GetChanRackOfs(self):

        if (self.MultiDeviceMode == MultiDev_Single) | (self.MultiDeviceMode == MultiDev_Master):
            if not channels.isHighLighted():
                self.ChanRackOfs = 0
            return self.ChanRackOfs
        else:
            return self.MasterDeviceChanRackOfs + SlaveModeLayoutYShift[self.SlaveModeLayout]

    def GetChanRackStartPos(self):

        if (self.MultiDeviceMode == MultiDev_Single) | (self.MultiDeviceMode == MultiDev_Master):
            if not channels.isHighLighted():
                self.ChanRackStartPos = 0
            return self.ChanRackStartPos
        else:
            return self.MasterDeviceChanRackStartPos + SlaveModeLayoutXShift[self.SlaveModeLayout]

    def GetClipOfs(self):

        if (self.MultiDeviceMode == MultiDev_Single) | (self.MultiDeviceMode == MultiDev_Master):
            return self.ClipOfs
        else:
            return self.MasterDeviceClipOfs + SlaveModeLayoutXShift[self.SlaveModeLayout]

    def GetGridRect(self, Mode):

        if Mode == ModeStepSeq:
            ofsX = self.GetChanRackStartPos()
            chanIdx = channels.channelNumber()
            if chanIdx < 0:
                chanIdx = 0
            r = utils.TRect(ofsX, chanIdx, 64, 1)

        elif Mode == ModePerf:
            ofsX = self.GetClipOfs()
            ofsY = self.GetTrackOfs() + 1
            r = utils.TRect(ofsX, ofsY, PadsW, PadsH)
            r.Right  += ofsX
            r.Bottom  += ofsY
        else:
            ofsX = 0
            ofsY = 0
            r = utils.TRect(ofsX, ofsY, PadsW, PadsH)

        Result = r

        if self.MultiDeviceMode == MultiDev_Single:
            Result = r
        elif self.MultiDeviceMode == MultiDev_Slave:
            Result = r  #Result = self.MasterDevice.GetGridRect(Mode)             #todo
            print('todo')
        else:  #is master
            for port, layout in self.SlavedDevices.items():
                if layout == SlaveModeLayout_Right:
                    r.Right += PadsW
                elif layout == SlaveModeLayout_Bottom:
                    r.Bottom += PadsH

            Result = r

        return Result

    def GetTrackOfs(self):

        if (self.MultiDeviceMode == MultiDev_Single) | (self.MultiDeviceMode == MultiDev_Master):
            return self.TrackOfs
        else:
            return self.MasterTrackOfs + SlaveModeLayoutYShift[self.SlaveModeLayout]

    def GetNoteModeName(self):
        return self.note_mode_handler.GetNoteModeName()

    def GetOmniNoteValue(self, Data1):
        return self.drum_mode_handler.GetOmniNoteValue(Data1)

    def GetSlicexNoteValue(self, Data1):
        return self.drum_mode_handler.GetSlicexNoteValue(Data1)

    def GetStepParam(self, Step, Param):
        index = channels.channelNumber()
        if index < 0:
            return -1
        stepPos = self.step_seq_handler.PadToStep(Step)
        return channels.getStepParam(0, Param, index, stepPos, 1)

    def GetCurStepParam(self, ChanIndex, Param):

        return channels.getCurrentStepParam(ChanIndex, self.CurStep, Param)

    def GetFPCNoteValue(self, Data1):
        return self.drum_mode_handler.GetFPCNoteValue(Data1)

    def OnIdle(self):

        def BlinkBtn(b, id):

            if not device.isAssigned():
                return
            if b:
                if self.BlinkTimer < BlinkSpeed:
                    self.SendCC(id, DualColorFull2)
                else:
                    self.SendCC(id, DualColorOff)
            else:
                self.SendCC(id, DualColorOff)

        #************

        if self.IdleDeviceCount == 0:
            self.IdleDeviceCount = self.FLFireDeviceCount
            self.AnalyzerHue = self.AnalyzerHue + 10
            if self.AnalyzerHue >= 360:
                self.AnalyzerHue = self.AnalyzerHue - 360
        else:
            self.IdleDeviceCount -= 1

        TopLineJustify = JustifyLeft
        if self.SlaveLayoutSelectionMode: # this mode takes over the other ones (it's "blocking")
            self.TopText = 'Slave device layout'
            self.DisplayTimedText(SlaveModeLayoutNamesT[self.SlaveModeLayout])
            self.TopTextTimer = 0
        elif self.TopTextTimer > 0:
            TopLineJustify = JustifyCenter
            self.TopTextTimer = self.TopTextTimer - device.getIdleElapsed()
            if self.TopTextTimer < 0:
                self.TopTextTimer = 0
        else:
            s = patterns.getPatternName(patterns.patternNumber())
            if transport.getLoopMode() == SM_Pat:
                self.TopText = s
            else:
                self.TopText = 'Song (' + s + ')'
            if self.LayoutSelectionMode:
                self.TopText = 'Layout select'
            elif self.CurrentMode == ModeStepEdit:
                try:
                    line1, line2 = self.step_edit_handler.GetDisplayText()
                    self.TopText = line1
                    self.DisplayText(Font6x8, JustifyLeft, TextRowHeight * TimedTextRow, line2, True)
                except Exception as e:
                    print('StepEdit display error: ' + str(e))

        self.CurStep = mixer.getSongStepPos() # set current playing step
        self.DisplayText(Font6x16 , TopLineJustify, 0, self.TopText, True)

        if self.AltHeld & self.ShiftHeld:
            self.JogWheelHeldTime = self.JogWheelHeldTime + 1
            if self.JogWheelHeldTime >= 120:
                self.JogWheelHeldTime = 0
                self.SetAsMasterDevice(not self.IsMasterDevice())
        else:
            self.JogWheelHeldTime = 0

        self.BlinkTimer += 1
        if self.BlinkTimer >= BlinkSpeed * 2:
            self.BlinkTimer = 0

        if (self.PatDownBtnHeld | self.PatUpBtnHeld) & (not self.AltHeld):
            self.PatBtnHeldTime  += 1
            if self.PatBtnHeldTime >= self.PatBtnHeldTriggerTime:
                self.PatBtnHeldTime = 0
                # resend pat up/down while button is held
                if self.PatBtnHeldTriggerTime > 2:
                    self.PatBtnHeldTriggerTime -= 1 # make it go faster & faster
                fakeMidi = TMidiEvent()
                fakeMidi.handled = 0
                fakeMidi.midiId = MIDI_NOTEON
                if self.PatDownBtnHeld:
                    fakeMidi.data1 = IDPatternDown
                else:
                    fakeMidi.data1 = IDPatternUp
                fakeMidi.data2 = 127
                OnMidiMsg(fakeMidi)
        else:
            self.PatBtnHeldTime = 0
            self.PatBtnHeldTriggerTime = HeldButtonRetriggerTime # reset to max time

        if (self.GridDownBtnHeld | self.GridUpBtnHeld) & (not self.BrowserMode):
            self.GridBtnHeldTime  +=   1
            if self.GridBtnHeldTime >= self.GridBtnHeldTriggerTime:
                self.GridBtnHeldTime = 0
                # resend Grid up/down while button is held
                if self.GridBtnHeldTriggerTime > 2:
                    self.GridBtnHeldTriggerTime -= 1 # make it go faster & faster
                fakeMidi = TMidiEvent()
                fakeMidi.handled = 0
                fakeMidi.midiId = MIDI_NOTEON
                if self.GridDownBtnHeld:
                    fakeMidi.data1 = IDBankR
                else:
                    fakeMidi.data1 = IDBankL
                fakeMidi.data2 = 127

                oldShift = self.ShiftHeld
                oldAlt = self.AltHeld
                self.ShiftHeld = False
                self.AltHeld = False
                OnMidiMsg(fakeMidi)
                self.ShiftHeld = oldShift
                self.AltHeld = oldAlt
        else:
            self.GridBtnHeldTime = 0
            self.GridBtnHeldTriggerTime = HeldButtonRetriggerTime # reset to max time

            if self.TextTimer > 0:
                self.TextTimer -= 1
                if self.TextTimer == 0:
                    self.DisplayTimedText(chr(13))

        if self.DisplayZoneTimer > 0:
            self.DisplayZoneTimer -= 1
            if self.DisplayZoneTimer == 0:
                playlist.lockDisplayZone(1 + self.GetTrackOfs(), False)

        if self.CurrentMode == ModeStepEdit:
            try:
                self.step_edit_handler.OnIdle()
            except Exception as e:
                print('StepEdit OnIdle error: ' + str(e))

        if self.CurrentMode == ModePerf:
            self.perf_mode_handler.OnIdle()
            # Refresh blink for pending pads and Play & Stop (any source)
            hasAny = any(len(d) > 0 for d in self.perf_mode_handler.PendingPerSource.values()) or \
                     any(len(d) > 0 for d in self.perf_mode_handler.PlayAndStopPerSource.values()) or \
                     self.perf_mode_handler._pendingPattern >= 0
            if hasAny:
                self.perf_mode_handler.Refresh()

        if self.CurrentMode == ModeChordSelect:
            self.chord_select_handler.OnIdle()

        self.UpdateCurrentKnobsMode()
        self.UpdateCurrentPadsMode()
        self.RefreshTransport()

        if self.ShiftHeld:
            # metronome status
            BlinkBtn(ui.isMetronomeEnabled(), IDPatternSong)
            # wait before rec
            BlinkBtn(ui.isStartOnInputEnabled(), IDPlay)
            # countdown
            BlinkBtn(ui.isPrecountEnabled(), IDStop)
            # looprec
            BlinkBtn(ui.isLoopRecEnabled(), IDRec)
            # snap
            BlinkBtn(ui.getSnapMode() != Snap_None, IDNote)
            # accent
            BlinkBtn(self.AccentMode, IDStepSeq)
            # overview
            BlinkBtn(False, IDPerform)
        else:
            self.UpdateCurrentModeBtns()

        self.display_mgr.UpdateScreenIdle()

    def Init(self):

        self.Reset()
        self.SetOfs(self.TrackOfs, self.ClipOfs)
        self.ClearDisplay()

    def IsLockedByReceiveNotesFrom(self):

        for n in range(0, channels.channelCount()):
            if channels.getChannelMidiInPort(n) == device.getPortNumber():
                return(n)
        return -1

    def IsMasterDevice(self):

        return self.MultiDeviceMode == MultiDev_Master

    def TranslateNote(self, event):

        Data1 = event.data1
        Data2 = 0

        Result = True
        if (Data1 >= PadFirst) & (Data1 <= PadLast):
            Data1 -= PadFirst
            Data2 = event.data2
        else:
            return True  # not a pad event, don't translate
        if self.CurrentMode == ModeNotes:
            Data2 = self.AdaptVelocity(Data2)
            col = Data1 % PadsStride
            if col >= 12:  # function pad, no note
                return False
            row = Data1 // PadsStride
            octave = PadsH - 1 - row  # bottom row = lowest octave
            Data1 = self.KeyOffset + (octave * 12) + col
            if Data1 < 0 or Data1 > 127:
                return False
        elif self.CurrentMode == ModeDrum:
            # FL Control mode keeps raw pad messages in the script pipeline.
            # The actual pad handling happens later in OnMidiMsg via fl_control_handler.
            Result = True

        if Result:
            event.data1 = Data1
            event.data2 = Data2       
        return Result

    def OnMidiIn(self, event):

        if ((event.status == MIDI_NOTEON) | (event.status == MIDI_NOTEOFF)) & utils.InterNoSwap(event.data1, IDKnob1, IDKnob4) & self.ShiftHeld:
            print('Ignored note on/off')
            return
        else:
            self.LastRawData1 = event.data1
            self.LastRawData2 = event.data2
            if ((event.status & 0xF0) in [MIDI_NOTEON, MIDI_NOTEOFF]) and (self.CurrentMode == ModeDrum):
                if (event.data1 >= PadFirst) and (event.data1 <= PadLast):
                    self.fl_control_handler.OnPadEvent(event, event.data1 - PadFirst)
                    event.handled = True
                    return
            if (event.status & 0xF0) in [MIDI_NOTEON, MIDI_NOTEOFF]:
                if not self.TranslateNote(event):
                    event.handled = False #todo
                    return
            if event.status == 0xF4:

                ID = event.sysex[4]
                data1 = event.sysex[7] + (event.sysex[8] << 7)
                data2 = event.sysex[9] + (event.sysex[10] << 7)
                data3 = event.sysex[11] + (event.sysex[12] << 7)
                
                if ID == SM_SetAsSlave:
                  self.SetAsSlaveDevice(data1)
                  self.DispatchMessageToDeviceScripts(SM_SlaveDeviceModeLayout, self.SlaveModeLayout, device.getPortNumber(), 0)
                elif ID == SM_SetAsSingle:
                  self.SetAsSingleDevice()
                elif ID == SM_MasterDeviceChanRackOfs:
                  if self.MultiDeviceMode == MultiDev_Slave:
                    self.MasterDeviceChanRackOfs = data1
                    self.SetChanRackOfs(0, False)
                elif ID == SM_MasterDeviceChanStartPos:
                  self.MasterDeviceChanRackStartPos = data1
                elif ID == SM_SlaveDeviceSetOfs:
                  if self.MultiDeviceMode == MultiDev_Master:
                    self.SetOfs(self.GetTrackOfs() + data1 - 128, self.GetClipOfs() + data2 - 128, False)
                    self.DispatchMessageToDeviceScripts(SM_MasterDeviceSetOfs, self.TrackOfs + 128, self.ClipOfs + 128, 0)
                elif ID == SM_MasterDeviceSetOfs:
                  if self.MultiDeviceMode == MultiDev_Slave:
                    self.MasterTrackOfs = data1 - 128
                    self.MasterClipOfs = data1 - 128
                    self.SetOfs(self.MasterTrackOfs, self.MasterClipOfs, False)
                elif ID == SM_SlaveDeviceStartPos:
                  if self.MultiDeviceMode == MultiDev_Master:
                    self.SetChanRackStartPos(self.GetChanRackStartPos() + data1 - 128, False)
                elif ID == SM_SlaveDeviceRackOfs:
                  if self.MultiDeviceMode == MultiDev_Master:
                    self.SetChanRackOfs(self.GetChanRackOfs() + data1 - 128, False)
                    self.DispatchMessageToDeviceScripts(SM_MasterDeviceChanRackOfs, self.ChanRackOfs, 0, 0)
                elif ID == SM_UpdateLiveMode:
                  if self.MultiDeviceMode == MultiDev_Slave:
                    self.OnUpdateLiveMode(1, playlist.trackCount())
                elif ID == SM_SlaveDeviceModeLayout:
                  if self.MultiDeviceMode == MultiDev_Master:
                    self.SlavedDevices[data2] = data1
                    # Adjust master step edit index based on slave layout
                    if data1 == SlaveModeLayout_Left:
                        self.StepEditDeviceIndex = 1  # slave is left = master shows later steps
                    else:
                        self.StepEditDeviceIndex = 0  # slave is right = master shows first steps
                    if self.CurrentMode == ModeStepEdit:
                        try:
                            self.step_edit_handler.ApplyMultiDeviceOffset()
                        except Exception:
                            pass
                elif ID == SM_SlaveUpdateDisplayZone:
                  if self.MultiDeviceMode == MultiDev_Master:
                    self.OnDisplayZone()
                elif ID == SM_StepEditSync:
                  if self.CurrentMode == ModeStepEdit:
                    baseStep = data1 - 128
                    pitchOfs = data2
                    self.step_edit_handler.OnStepEditSync(baseStep, pitchOfs)

                event.handled = True

    def GetTimeForPad(self, Device, PadNum):
        Result = (self.GetChanRackStartPos() + PadNum - ((PadNum // PadsStride) * PadsStride)) * RecPPS

    def GetChannelNumForPad(self, PadNum):

        Result = -1

        if self.CurrentMode == ModeStepSeq:
            Result = channels.channelNumber()

        return Result

    def GetEventForPad(self, PadNum):

        Result = -1
        chNum = self.GetChannelNumForPad(Device, PadNum)
        if chNum > -1:
            cID = channels.getChannelIndex(chNum)
            Time = self.GetTimeForPad(Device, PadNum)
            if Assigned(PatInfoT[patterns.patternNumber()].NoteRecChan):
                for i in range(0, Count):
                    Event = pNoteEvent(GetEventAtPos(i))
                    if (Event.ChanID == cID) & (((Event.Time // RecPPS) * RecPPS) == Time):
                        Result = pRecEvent(Event)
                        return

        return Result

    def OnMidiMsg(self, event):

        tempHeldPads = bytearray()
        ParamNames = ('Step pitch', 'Velocity', 'Release', 'Fine pitch', 'Panning', 'Mod X', 'Mod Y', 'Shift')
        
        def SetStep(padNum, Force):

            Result = False
            index = channels.channelNumber()
            if index < 0:
                return Result
            stepPos = self.step_seq_handler.PadToStep(padNum)
            general.saveUndo('Fire: Step seq edit', UF_PR, True)
            if self.CurrentMode == ModeStepSeq:
                if channels.isGridBitAssigned(index):
                    if Force:
                        if channels.getGridBit(index, stepPos) == 0:
                            channels.setGridBit(index, stepPos, 1)
                        Result = True
                    else:
                        if channels.getGridBit(index, stepPos) > 0:
                            channels.setGridBit(index, stepPos, 0)
                        else:
                            channels.setGridBit(index, stepPos, 1)
                            Result = True
            return Result

        def HandleStepSeqPad(id, padNum):

            # store pads being held
            if id == MIDI_NOTEON:
                self.HeldPads.append(padNum)
            else:
                for i in range(0, len(self.HeldPads)):
                    if self.HeldPads[i] != padNum:
                        tempHeldPads.append(self.HeldPads[i])

                self.HeldPads = bytearray(len(tempHeldPads))
                for i in range(0, len(tempHeldPads)):
                    self.HeldPads[i] = tempHeldPads[i]

            didSetStep = False
            if id == MIDI_NOTEOFF:
                didSetStep = SetStep(padNum, self.HeldPadsChanged) # if we tweaked a param, force the step on upon releasing

            if self.AccentMode & didSetStep:
                self.SetStepParam(padNum, pPitch, self.AccentParams.Pitch)
                self.SetStepParam(padNum, pVelocity, self.AccentParams.Vel)
                self.SetStepParam(padNum, pPan, self.AccentParams.Pan)
                self.SetStepParam(padNum, pModX, self.AccentParams.ModX)
                self.SetStepParam(padNum, pModY, self.AccentParams.ModY)
                channels.updateGraphEditor()

            if len(self.HeldPads) == 0:
                self.HeldPadsChanged = False
                channels.closeGraphEditor(True)

        def HandleKnob(ID, Data2, Name, Bipolar):
            mixer.automateEvent(ID, Data2, REC_MIDIController, 0, 1, EKRes)
            barVal = device.getLinkedValue(ID)
            self.DisplayBar(Name, barVal, Bipolar)

        def HandleHeldPadsParam(Data2, Param):

            ParamDefVal = (DotNote_Default, 100, 64, 120, 64, 128, 128, 0)
            ParamMax = (127, 127, 127, 240, 127, 255, 255, 255)
            ParamInc = (1, 2, 2, 2, 2, 2, 2, 1)
            RecPPS = mixer.getRecPPS()

            index = channels.channelNumber()
            if index < 0:
                return

            for m in range(0, len(self.HeldPads)):
                stepPos = self.step_seq_handler.PadToStep(self.HeldPads[m])

                if (Param == pShift) & (channels.getGridBit(index, stepPos) == 0):
                    channels.setGridBit(index, stepPos, 1)

                val = self.GetStepParam(self.HeldPads[m], Param)
                oldVal = val

                if val == -1:
                    val = ParamDefVal[Param]

                if Data2 >= 0x7F // 2:
                    Data2 = -(0x80 - Data2)

                if Data2 > 0:
                    val += ParamInc[Param]
                else:
                    val -=  ParamInc[Param]

                if Param == pShift: # other parameters will be limited by graph editor
                    oldVal = (oldVal // RecPPS) * RecPPS
                    val = utils.Limited(val, oldVal, oldVal + RecPPS - 1)
                self.SetStepParam(self.HeldPads[m], Param, val)

                if Param != pShift:
                    val = utils.Limited(val, 0, ParamMax[Param])

                if m == 0:
                    if Param == pPitch:
                        self.DisplayTimedText(ParamNames[Param] + ': ' + utils.GetNoteName(val))
                    else:
                        if Param == pShift:
                            val = val % RecPPS
                            self.DisplayBar(ParamNames[Param] + ': ' + str(val), val / (RecPPS - 1), False)
                        else:
                            bipolar = (Param == pFinePitch) | (Param == pPan)
                            if bipolar:
                                showVal = val - ParamMax[Param] // 2
                            else:
                                showVal = val
                            self.DisplayBar(ParamNames[Param] + ': ' + str(showVal), val / ParamMax[Param], bipolar)

                channels.updateGraphEditor()

        def SetChanLoop(ChanIndex, LoopLength):

            loopName = patterns.setChannelLoop(ChanIndex, LoopLength)
            self.DisplayTimedText(channels.getChannelName(ChanIndex) + ' loop: ' + loopName)
            self.DidTweakLooping = True

        #************
        # treat self.SlaveLayoutSelectionMode in priority as it's a mode that should lock all others
        screen.unBlank(True)
        event.data1 = self.LastRawData1
        event.data2 = self.LastRawData2

        if (not event.handled):
            if self.SlaveLayoutSelectionMode:
                if (event.midiId == MIDI_CONTROLCHANGE) & (event.data1 == IDJogWheel):
                    if event.data2 == 1:
                        self.SlaveModeLayout  +=  1
                    else:
                        self.SlaveModeLayout -= 1
                    if self.SlaveModeLayout > SlaveModeLayout_Last:
                        self.SlaveModeLayout = 0
                    elif self.SlaveModeLayout < 0:
                        self.SlaveModeLayout = SlaveModeLayout_Last
                    self.DispatchMessageToDeviceScripts(SM_SlaveDeviceModeLayout, self.SlaveModeLayout, device.getPortNumber(), 0)
                    self.UpdateSlaveStepEditIndex()
                    self.DisplayTimedText(SlaveModeLayoutNamesT[self.SlaveModeLayout])
                elif (event.midiId == MIDI_NOTEON) & (event.data1 == IDJogWheelDown):
                    self.SlaveLayoutSelectionMode = False
                    if self.CurrentMode == ModeStepSeq:
                        self.SetChanRackStartPos(self.GetChanRackStartPos())
                    elif self.CurrentMode == ModePerf:
                        self.SetOfs(self.TrackOfs, self.ClipOfs)
                    elif self.CurrentMode == ModeStepEdit:
                        try:
                            self.step_edit_handler.ApplyMultiDeviceOffset()
                        except Exception:
                            pass
                    self.DisplayTimedText('')
                    self.ClearBtnMap()
                    self.UpdateCurrentPadsMode()
                    event.handled = True
                return

        if (not event.handled):
            if (event.data1 == IDKnob1) & (event.data2 != 0) & self.AltHeld:
                i = event.data2
                if (i >= 64) & (i <= 127):
                    i -= 128
                self.FLFirePadBrightness = utils.Limited(self.FLFirePadBrightness + i, 32, 128)
                self.DisplayBar('Pad brightness', (self.FLFirePadBrightness - 32) / 96, False)
                ui.setHintMsg(str(round(100 * ((self.FLFirePadBrightness - 32) / 96))) + '% Pad brightness')
                self.OnUpdateLiveMode(1, playlist.trackCount())
                event.handled = True
            if (event.data1 == IDKnob2) & (event.data2 != 0) & self.AltHeld:
                i = event.data2
                if (i >= 64) & (i <= 127):
                    i -= 128
                self.FLFirePadSaturation = utils.Limited(self.FLFirePadSaturation + i, 0, 128)
                self.DisplayBar('Pad saturation', (self.FLFirePadSaturation) / 96, False)
                ui.setHintMsg(str(round(100 * (self.FLFirePadSaturation / 128))) + '% Pad saturation')
                self.OnUpdateLiveMode(1, playlist.trackCount())
                event.handled = True
            if (event.data1 == IDKnob3) & (event.data2 != 0) & self.AltHeld:
                i = event.data2
                if (i >= 64) & (i <= 127):
                    i -= 128
                self.KnobsV[2]  += i
                if self.KnobsV[2] <= -32:
                    self.KnobsV[2]  += 32
                elif self.KnobsV[2] >= 32:
                    self.KnobsV[2] -= 32
                else:
                    i = 0
                if i != 0:
                    if (self.CurrentMode < ModePadVisFirst) | (self.CurrentMode > ModePadVisLast):
                        self.NonVisMode = self.CurrentMode
                        if self.Sign(i) > 0:
                            self.CurrentMode = ModePadVisFirst
                        else:
                            self.CurrentMode = ModePadVisLast
                    else:
                        self.CurrentMode = self.CurrentMode + self.Sign(i)
                        if (self.CurrentMode < ModePadVisFirst) | (self.CurrentMode > ModePadVisLast):
                            self.CurrentMode = ModeAnalyzerNone
                        print(self.CurrentMode)
                        self.TopText = ModeVisNamesT[0]

                    if self.CurrentMode == ModeAnalyzerNone:
                        self.CurrentMode = self.NonVisMode
                    else:
                        self.TopText = ModeVisNamesT[self.CurrentMode + 1 - ModePadVisFirst]
                        self.SetAnalyzerMode(self.CurrentMode)
                    self.TopTextTimer = TextDisplayTime
                event.handled = True

            if (event.data1 == IDKnob4) & (event.data2 != 0) & self.AltHeld:
                i = event.data2
                if (i >= 64) & (i <= 127):
                    i -= 128
                self.KnobsV[3]  += i
                if self.KnobsV[3] <= -32:
                    self.KnobsV[3]  += 32
                elif self.KnobsV[3] >= 32:
                    self.KnobsV[3] -= 32
                else:
                    i = 0
                if i != 0:
                    if (self.ScreenMode < ScreenModeFirst) | (self.ScreenMode > ScreenModeLast):
                        if self.Sign(i) > 0:
                            i = ScreenModeFirst
                        else:
                            i = ScreenModeLast
                    else:
                        i = self.ScreenMode + self.Sign(i)
                        if (i < ScreenModeFirst) | (i > ScreenModeLast):
                            i = ScreenModeNone
                        self.TopText = ScreenModeNamesT[0]

                    if i != ScreenModeNone:
                        self.TopText = ScreenModeNamesT[i + 1 - ScreenModeFirst]
                    self.TopTextTimer = TextDisplayTime
                    self.SetScreenMode(i)

                event.handled = True

        if not event.handled:
            if screen.menuShowing():
                if (event.midiId == MIDI_CONTROLCHANGE) & (event.data1 == IDJogWheel):
                    if (event.data2 >= 1) & (event.data2 <= 63):
                        screen.MenuNext()
                    elif (event.data2 >= 64) & (event.data2 <= 127):
                        screen.menuPrev()
                    event.handled = True
                elif (event.midiId == MIDI_NOTEON) & (event.data1 == IDJogWheelDown):
                    screen.menuItemClick()
                    event.handled = True

        if not event.handled:
            if event.midiId == MIDI_CONTROLCHANGE:
                event.handled = True
                if event.data1 == IDJogWheel:
                    HeldMuteBtn = -1
                    for n in range(0, 4):
                        if self.MuteBtnStates[n]:
                            HeldMuteBtn = n
                            break

                    if HeldMuteBtn >= 0:
                        p = patterns.getChannelLoopStyle(patterns.patternNumber(), HeldMuteBtn + self.GetChanRackOfs())
                        if event.data2 == 1:
                            p += 1
                        else:
                            p -= 1
                        SetChanLoop(HeldMuteBtn + self.GetChanRackOfs(), p)

                    else:
                        if self.ShiftHeld & (self.CurrentMode != ModePerf) & (not self.BrowserMode):
                            if event.data2 == 1:
                                transport.globalTransport(FPT_TrackJog, 1)
                            else:
                                transport.globalTransport(FPT_TrackJog, -1)
                            self.CurrentMixerTrack = mixer.trackNumber()
                            self.DisplayTimedText('Mixer : ' + mixer.getTrackName(self.CurrentMixerTrack))

                        elif self.AltHeld & (not self.BrowserMode) & (self.CurrentMode != ModeStepEdit):

                            m = channels.selectedChannel()
                            if event.data2 == 1:
                                m += 1
                            else:
                                m -= 1
                            m = utils.Limited(m, 0, channels.channelCount() - 1)
                            channels.selectOneChannel(m) #this use group index
                            self.DisplayTimedText('Chan: ' + channels.getChannelName(m))

                            if ui.getVisible(widChannelRack):
                                R = self.GetGridRect(ModeStepSeq)
                                ui.crDisplayRect(R.Left, R.Top, R.Right, R.Bottom, 2000)

                        elif (self.CurrentMode == ModeStepSeq) & self.MixerTrackSelectionMode:

                            m = channels.channelNumber()
                            if m < 0:
                                return
                            p = channels.getTargetFxTrack(m)
                            if event.data2 == 1:
                                p += 1
                            else:
                                p -= 1
                            p = utils.Limited(p, 0, mixer.trackCount() - 1)
                            general.processRECEvent(channels.getRecEventId(m) + REC_Chan_FXTrack, p, REC_Control | REC_UpdateControl)
                            mixer.setTrackNumber(p, curfxScrollToMakeVisible | curfxMinimalLatencyUpdate)
                            self.DisplayTimedText('Chan ' + str(m + 1) + chr(13) + 'Track: ' + mixer.getTrackName(channels.getTargetFxTrack(m)))

                        elif (self.CurrentMode == ModeStepSeq) & self.AccentMode:

                            if event.data2 == 1:
                                self.AccentParams.Pitch += 1
                            else:
                                self.AccentParams.Pitch -= 1
                            self.AccentParams.Pitch = utils.Limited(self.AccentParams.Pitch, 0, 127)
                            self.DisplayTimedText('Default pitch : ' + utils.GetNoteName(self.AccentParams.Pitch))

                        elif (self.CurrentMode == ModeDrum) & self.LayoutSelectionMode:
                            if event.data2 == 1:
                                self.CurrentDrumMode  += 1
                            else:
                                self.CurrentDrumMode -= 1
                            if self.CurrentDrumMode > DrumModeLast:
                                self.CurrentDrumMode = 0
                            elif self.CurrentDrumMode < 0:
                                self.CurrentDrumMode = DrumModeLast
                            self.CutPlayingNotes()
                            self.ClearBtnMap()
                            self.drum_mode_handler.Refresh()
                            self.DisplayTimedText(DrumModesNamesT[self.CurrentDrumMode])

                        elif self.BrowserMode:
                            text = ui.navigateBrowserMenu(event.data2, self.ShiftHeld)
                            if text != '':
                                self.DisplayTimedText(text)

                        elif (self.CurrentMode == ModeStepSeq) | (self.CurrentMode == ModeNotes) | (self.CurrentMode == ModeDrum):

                            if (len(self.HeldPads) >= 1) & (self.CurrentMode == ModeStepSeq):
                                HandleHeldPadsParam(event.data2, pPitch)
                                p = self.HeldPads[0] - (self.HeldPads[0] // PadsStride) * PadsStride
                                chNum = self.GetChannelNumForPad(self.HeldPads[0])
                                if ui.getVisible(widChannelRack) & (chNum > -1):
                                    channels.showGraphEditor(False, pPitch, p, channels.getChannelIndex(chNum), 0)
                                self.HeldPadsChanged = True

                            else:
                                m = channels.selectedChannel()
                                if event.data2 == 1:
                                    m += 1
                                else:
                                    m -= 1
                                m = utils.Limited(m, 0, channels.channelCount() - 1)
                                channels.selectOneChannel(m)
                                if ui.getVisible(widChannelRack):
                                    R = self.GetGridRect(ModeStepSeq)
                                    ui.crDisplayRect(R.Left, R.Top, R.Right, R.Bottom, 2000)
                                self.DisplayTimedText('Chan: ' + channels.getChannelName(m))

                        elif self.CurrentMode == ModePerf:
                            self.perf_mode_handler.OnJogWheel(event)

                        elif self.CurrentMode == ModeStepEdit:
                            if event.data2 == 1:
                                m = 1
                            else:
                                m = -1
                            if self.ShiftHeld:
                                txt = self.step_edit_handler.ScrollPitch(m)
                            else:
                                txt = self.step_edit_handler.ScrollSteps(m)
                            self.DisplayTimedText(txt)

                        elif self.CurrentMode == ModeChordSelect:
                            if event.data2 == 1:
                                m = 1
                            else:
                                m = -1
                            txt = self.chord_select_handler.ScrollChord(m)
                            self.DisplayTimedText(txt)

                elif event.data1 in [IDKnob1, IDKnob2, IDKnob3, IDKnob4]:
                    event.inEv = event.data2
                    if event.inEv >= 0x40:
                        event.outEv = event.inEv - 0x80
                    else:
                        event.outEv = event.inEv
                    event.isIncrement = 1
                    if self.CurrentMode == ModeStepEdit:
                        if self.step_edit_handler.EditMode:
                            txt = self.step_edit_handler.OnKnobEdit(event.data1, self.AdaptKnobVal(event.outEv))
                            if txt:
                                self.DisplayTimedText(txt)
                        elif event.data1 == IDKnob1:
                            m = 1 if event.data2 < 64 else -1
                            txt = self.step_edit_handler.ScrollPitch(m, 1)
                            if txt:
                                self.DisplayTimedText(txt)

                    elif (self.CurrentKnobsMode == KnobsModeChannelRack) & (self.CurrentMode == ModeStepSeq) & self.AccentMode:

                        if event.data1 == IDKnob1:
                            self.AccentParams.Vel = utils.Limited(self.AccentParams.Vel + self.AdaptKnobVal(event.outEv), 0, 127)
                            self.DisplayBar('Default velocity', self.AccentParams.Vel / 127, False)
                        elif event.data1 == IDKnob2:
                            self.AccentParams.Pan = utils.Limited(self.AccentParams.Pan + self.AdaptKnobVal(event.outEv), 0, 127)
                            self.DisplayBar('Default panning', self.AccentParams.Pan / 127, True)
                        elif event.data1 == IDKnob3:
                            self.AccentParams.ModX = utils.Limited(self.AccentParams.ModX + self.AdaptKnobVal(event.outEv), 0, 127)
                            self.DisplayBar('Default ModX', self.AccentParams.ModX / 127, False)
                        elif event.data1 == IDKnob4:
                            self.AccentParams.ModY = utils.Limited(self.AccentParams.ModY + self.AdaptKnobVal(event.outEv), 0, 127)
                            self.DisplayBar('Default ModY', self.AccentParams.ModY / 127, False)

                    elif (len(self.HeldPads) >= 1) & (self.CurrentMode == ModeStepSeq):
                        if event.data1 == IDKnob1:
                            HandleHeldPadsParam(event.data2, pVelocity)
                        elif event.data1 == IDKnob2:
                            HandleHeldPadsParam(event.data2, pPan)
                        elif event.data1 == IDKnob3:
                            HandleHeldPadsParam(event.data2, pModX)
                        elif event.data1 == IDKnob4:
                            HandleHeldPadsParam(event.data2, pModY)

                        self.HeldPadsChanged = True
                        self.ChangeFlag = True

                    elif self.CurrentKnobsMode == KnobsModeChannelRack:
                        selChanNum = channels.channelNumber()
                        if selChanNum < 0:
                            return
                        if event.data1 == IDKnob1:
                            HandleKnob(channels.getRecEventId(selChanNum) + REC_Chan_Vol, self.AdaptKnobVal(event.outEv), 'Chan Volume', False)
                        elif event.data1 == IDKnob2:
                            HandleKnob(channels.getRecEventId(selChanNum) + REC_Chan_Pan, self.AdaptKnobVal(event.outEv), 'Chan Panning', True)
                        elif event.data1 == IDKnob3:
                            HandleKnob(channels.getRecEventId(selChanNum) + REC_Chan_FCut, self.AdaptKnobVal(event.outEv), 'Chan Filter Freq', False)
                        elif event.data1 == IDKnob4:
                            HandleKnob(channels.getRecEventId(selChanNum) + REC_Chan_FRes, self.AdaptKnobVal(event.outEv), 'Chan Filter BW', False)

                    elif self.CurrentKnobsMode == KnobsModeMixer:

                        self.CurrentMixerTrack = mixer.trackNumber()
                        if (self.CurrentMixerTrack < 0) | (self.CurrentMixerTrack >= mixer.getTrackInfo(TN_Sel)):
                            return

                        if event.data1 == IDKnob1:
                            HandleKnob(REC_Mixer_Vol + mixer.getTrackPluginId(self.CurrentMixerTrack, 0), self.AdaptKnobVal(event.outEv), mixer.getTrackName(self.CurrentMixerTrack) + ' Vol', False)
                        if event.data1 == IDKnob2:
                            HandleKnob(REC_Mixer_Pan + mixer.getTrackPluginId(self.CurrentMixerTrack, 0), self.AdaptKnobVal(event.outEv), mixer.getTrackName(self.CurrentMixerTrack) + ' Pan', True)
                        if event.data1 == IDKnob3:
                            HandleKnob(REC_Mixer_EQ_Gain + 0 + mixer.getTrackPluginId(self.CurrentMixerTrack, 0), self.AdaptKnobVal(event.outEv), mixer.getTrackName(self.CurrentMixerTrack) + ' EQ Lo', True)
                        if event.data1 == IDKnob4:
                            HandleKnob(REC_Mixer_EQ_Gain + 2 + mixer.getTrackPluginId(self.CurrentMixerTrack, 0), self.AdaptKnobVal(event.outEv), mixer.getTrackName(self.CurrentMixerTrack) + ' EQ Hi', True)

                    else:
                        event.handled = False # user modes, free
                        try:
                            event.data1 += (self.CurrentKnobsMode - KnobsModeUser1) * 4 # so the CC is different for each user mode
                            if (general.getVersion() > 10):
                              event.res = EKRes
                            device.processMIDICC(event)
                            if (general.getVersion() > 9):
                              BaseID = EncodeRemoteControlID(device.getPortNumber(), 0, 0)
                              eventId = device.findEventID(BaseID + event.data1, 0)
                              if eventId != 2147483647:
                                s = device.getLinkedParamName(eventId)
                                s2 = device.getLinkedValueString(eventId)
                                self.TopText = s
                                self.DisplayTimedText(s2)
                                self.TopTextTimer = TextDisplayTime
                        except Exception:
                            self.DisplayTimedText('User ' + str(self.CurrentKnobsMode - KnobsModeUser1 + 1) + ': No link')

                # NOTE
            if event.midiId in [MIDI_NOTEON, MIDI_NOTEOFF]:
                if (event.data1 >= PadFirst) & (event.data1 <= PadLast):
                    event.data1 -= PadFirst # event.data1 is now 0..63
                    HeldMuteBtn = -1
                    for n in range(0, 4):
                        if self.MuteBtnStates[n]:
                            HeldMuteBtn = n
                            break
                    if (HeldMuteBtn >= 0) & (self.CurrentMode == ModeStepSeq):
                        y = event.data1 // PadsStride
                        x = event.data1 - y * PadsStride
                        if y == HeldMuteBtn:
                            SetChanLoop(HeldMuteBtn + self.GetChanRackOfs(), x + 1 + self.GetChanRackStartPos())
                    else:
                        if self.CurrentMode == ModeDrum: # FL Control mode
                            self.fl_control_handler.OnPadEvent(event, event.data1)

                        elif self.CurrentMode == ModeNotes: # piano mode
                            self.note_mode_handler.OnPadEvent(event, event.data1)
                            return
                        elif (self.CurrentMode == ModeStepSeq):
                            HandleStepSeqPad(event.midiId, event.data1)
                        elif self.CurrentMode == ModePerf:
                            self.perf_mode_handler.OnPadEvent(event, event.data1)
                        elif self.CurrentMode == ModeStepEdit:
                            self.step_edit_handler.OnPadEvent(event, event.data1)

                elif event.data1 in [IDMute1, IDMute2, IDMute3, IDMute4]:
                    c = event.data1 - IDMute1 # so it's 0..3
                    self.MuteBtnStates[c] = (event.midiId == MIDI_NOTEON)
                    if event.midiId == MIDI_NOTEOFF:
                        if (not self.DidTweakLooping) & (self.CurrentMode in [ModeStepSeq, ModeNotes]):
                            if not utils.InterNoSwap(c + self.GetChanRackOfs(), 0, channels.channelCount() - 1):
                                return
                            m = c + self.GetChanRackOfs();
                            if self.AltHeld:
                                self.CutPlayingNotes()
                                channels.selectOneChannel(m)
                            else:
                                if not self.ShiftHeld:
                                    channels.muteChannel(m)
                                else:
                                    channels.soloChannel(m)
                            self.DisplayTimedText('Chan: ' + channels.getChannelName(m))

                        elif self.CurrentMode == ModeDrum:
                            txt = self.fl_control_handler.HandleMuteButton(c)
                            if txt:
                                self.DisplayTimedText(txt)

                        elif self.CurrentMode == ModePerf:
                            # Mute buttons: switch source (0=Mixer, 1=ChannelRack, 2=Playlist, 3=Pattern)
                            from fire_modules.perf_mode import SRC_NAMES
                            self.perf_mode_handler.SourceMode = c
                            self.perf_mode_handler.PendingChanges.clear()
                            self.perf_mode_handler._pendingPattern = -1
                            self.perf_mode_handler.PadOffset = 0
                            self.ClearBtnMap()
                            self.perf_mode_handler.Refresh()
                            self.DisplayTimedText('Perf: ' + SRC_NAMES[c])

                        elif self.CurrentMode == ModeStepEdit:
                            txt = self.step_edit_handler.ToggleStepMute(c)
                            if txt:
                                self.DisplayTimedText(txt)
                        self.DidTweakLooping = False

                # shift key
                elif event.data1 == IDShift:
                    self.ShiftHeld = event.midiId == MIDI_NOTEON
                    if event.midiId == MIDI_NOTEON:
                        self.BlinkTimer = 0

                # jogwheel button
                elif event.data1 == IDJogWheelDown:

                    self.JogWheelPushed = event.midiId == MIDI_NOTEON
                    HeldMuteBtn = -1
                    for n in range(0, 3):
                        if self.MuteBtnStates[n]:
                            HeldMuteBtn = n
                            break

                    if (HeldMuteBtn >= 0) & self.JogWheelPushed:
                        p = patterns.getChannelLoopStyle(patterns.patternNumber(), HeldMuteBtn + self.GetChanRackOfs())
                        if (p != ssLoopOff):
                            if (general.getVersion() > 8):
                              patterns.burnLoop(HeldMuteBtn + self.GetChanRackOfs())
                              self.DisplayTimedText(channels.getChannelName(n + self.GetChanRackOfs()) + ': burn loop')
                            else:
                              self.DisplayTimedText('Not implemented in this version!')

                        self.DidTweakLooping = True

                    else:
                        if self.BrowserMode & self.JogWheelPushed:
                            if not ui.getVisible(widBrowser):
                                return
                            #SampleListForm.SetFocus
                            nodeFileType = ui.getFocusedNodeFileType()
                            if nodeFileType == -1:
                                return
                            self.DisplayTimedText(ui.getFocusedNodeCaption())
                            if nodeFileType <= -100:
                                transport.globalTransport(FPT_Enter, 1, PME_System | PME_FromMIDI) # expand/collapse folder
                            else:
                                ui.selectBrowserMenuItem()

                        elif (self.CurrentMode == ModeNotes) & self.JogWheelPushed & (channels.channelNumber(True) >= 0):
                            # Jog Push in Piano mode = toggle Chord Mode
                            self.note_mode_handler.ChordMode = not self.note_mode_handler.ChordMode
                            self.DisplayTimedText(self.note_mode_handler.GetNoteModeName())
                            self.note_mode_handler.Refresh()

                        elif (self.CurrentMode == ModeDrum) & self.JogWheelPushed & (channels.channelNumber(True) >= 0):
                            self.LayoutSelectionMode = not self.LayoutSelectionMode
                            if self.LayoutSelectionMode:
                                self.DisplayTimedText(DrumModesNamesT[self.CurrentDrumMode])

                        elif (self.CurrentMode == ModePerf) & self.JogWheelPushed:
                            self.perf_mode_handler.OnJogPush()

                        elif (self.CurrentMode == ModeStepEdit) & self.JogWheelPushed:
                            try:
                                if self.AltHeld:
                                    # PUSH: save both MIDI (for FL exchange) and JSON (for faithful state)
                                    pathMidi = self.step_edit_handler.SaveMidiFile()
                                    pathJson = self.step_edit_handler.SaveJsonFile()
                                    if pathMidi and pathJson:
                                        self.DisplayTimedText('PUSH OK' + chr(13) + 'MIDI+JSON saved')
                                    elif pathMidi or pathJson:
                                        okParts = []
                                        if pathMidi:
                                            okParts.append('MIDI')
                                        if pathJson:
                                            okParts.append('JSON')
                                        self.DisplayTimedText('PUSH PARTIAL' + chr(13) + '+'.join(okParts) + ' saved')
                                    else:
                                        err = self.step_edit_handler.LastFileError
                                        self.DisplayTimedText('PUSH FAIL' + chr(13) + (err[:18] if err else 'Save error'))
                                        print('PUSH FAIL: MIDI path=' + str(pathMidi) + ', JSON path=' + str(pathJson) + ', err=' + str(err))
                                elif self.ShiftHeld:
                                    # PULL: try JSON first (faithful), fallback to MIDI
                                    ok = self.step_edit_handler.LoadJsonFile()
                                    if ok:
                                        self.step_edit_handler.SyncAllToFL()
                                        self.step_edit_handler.Refresh()
                                        self.DisplayTimedText('PULL JSON OK' + chr(13) + 'Synced to FL')
                                    else:
                                        ok = self.step_edit_handler.LoadMidiFile()
                                        if ok:
                                            self.step_edit_handler.SyncAllToFL()
                                            self.step_edit_handler.Refresh()
                                            self.DisplayTimedText('PULL MIDI OK' + chr(13) + 'Synced to FL')
                                        else:
                                            err = self.step_edit_handler.LastFileError
                                            self.DisplayTimedText('PULL FAIL' + chr(13) + ((err[:18]) if err else 'No file found'))
                                else:
                                    self.step_edit_handler.SyncAllToFL()
                                    self.DisplayTimedText('Sync to FL OK')
                            except Exception as e:
                                print('StepEdit Jog error: ' + str(e))
                                self.DisplayTimedText('JOG ERROR' + chr(13) + str(e)[:20])

                        elif (self.CurrentMode == ModeStepSeq) & self.JogWheelPushed & (not self.AltHeld) & (channels.channelNumber(True) >= 0):
                            self.MixerTrackSelectionMode = not self.MixerTrackSelectionMode
                            if self.MixerTrackSelectionMode & utils.Limited(channels.channelNumber(), 0, channels.channelCount() - 1) & utils.Limited(channels.getTargetFxTrack(channels.channelNumber()), 0, mixer.trackCount() - 1):
                                self.DisplayTimedText('Chan ' + str(channels.channelNumber() + 1) + chr(13) + 'Track: ' + mixer.getTrackName(channels.getTargetFxTrack(channels.channelNumber())))
                            else:
                                self.DisplayTimedText(chr(13))

                # browser button
                elif event.data1 == IDBrowser:
                    if (event.midiId == MIDI_NOTEON):

                        if self.ShiftHeld:
                            transport.globalTransport(FPT_Undo, 1, event.pmeFlags)
                        elif self.AltHeld:
                            # Alt + Browser = FL Browser (classic behavior)
                            self.BrowserMode = not self.BrowserMode
                            if self.BrowserMode:
                                self.LayoutSelectionMode = False
                                if not ui.getVisible(widBrowser):
                                    ui.showWindow(widBrowser)
                                    self.BrowserShouldClose = True

                                if ui.isBrowserAutoHide():
                                    ui.setBrowserAutoHide(False)
                                    self.BrowserShouldAutoHide = True

                                #todo SampleListForm.SetFocus
                                self.DisplayTimedText('Browser')
                            else:
                                if self.BrowserShouldAutoHide & (not ui.isBrowserAutoHide()):
                                    ui.setBrowserAutoHide(True)

                                if self.BrowserShouldClose & ui.getVisible(widBrowser):
                                    ui.showWindow(widBrowser)
                                self.BrowserShouldAutoHide = False
                                self.BrowserShouldClose = False
                                if ui.getVisible(widChannelRack):
                                    ui.setFocused(widChannelRack)
                                self.ShowCurrentPadMode()
                        else:
                            # Browser = toggle Chord Select mode ON/OFF
                            if self.CurrentMode == ModeChordSelect:
                                # Already in ChordSelect -> return to previous mode
                                self.CurrentMode = self.ModeBeforeChordSelect
                                self.ShowCurrentPadMode()
                            else:
                                # Enter ChordSelect, save current mode to return to
                                self.ModeBeforeChordSelect = self.CurrentMode
                                self.CurrentMode = ModeChordSelect
                                self.chord_select_handler.OnActivate()
                                self.DisplayTimedText(self.chord_select_handler.GetDisplayText())

                # Alt button
                elif event.data1 == IDAlt:
                    self.AltHeld = event.midiId == MIDI_NOTEON

                # navigation
                elif event.data1 == IDPatternUp:
                    self.PatUpBtnHeld = (event.midiId == MIDI_NOTEON)
                    if (event.midiId == MIDI_NOTEON) & (self.CurrentMode == ModeStepEdit):
                        txt = self.step_edit_handler.ScrollStepsSingle(-1)
                        self.DisplayTimedText(txt)
                    elif (event.midiId == MIDI_NOTEON) & (self.CurrentMode == ModeNotes):
                        self.CutPlayingNotes()
                        self.KeyOffset = utils.Limited(self.KeyOffset + 12, 12, 96)
                        self.ClearBtnMap()
                        self.note_mode_handler.Refresh()
                        self.DisplayTimedText('Octave: ' + self.note_mode_handler.GetOctaveRangeText())
                    elif (event.midiId == MIDI_NOTEON) & (patterns.patternNumber() > 1) & ((self.CurrentMode == ModeStepSeq) | (self.CurrentMode == ModeDrum)):
                        patterns.jumpToPattern(patterns.patternNumber() - 1)
                    elif self.CurrentMode == ModePerf:
                        if self.ShiftHeld:
                            ofsIncrement = 1
                        else:
                            ofsIncrement = 4
                        if (event.midiId == MIDI_NOTEON):
                            self.SetOfs(self.GetTrackOfs() - ofsIncrement, self.GetClipOfs())
                        playlist.lockDisplayZone(1 + self.GetTrackOfs(), event.data2 > 0)

                    self.SendCC(IDPatternUp, int(event.midiId == MIDI_NOTEON) * SingleColorFull)

                elif event.data1 == IDPatternDown:

                    self.PatDownBtnHeld = (event.midiId == MIDI_NOTEON)
                    if (event.midiId == MIDI_NOTEON) & (self.CurrentMode == ModeStepEdit):
                        txt = self.step_edit_handler.ScrollStepsSingle(1)
                        self.DisplayTimedText(txt)
                    elif (event.midiId == MIDI_NOTEON) & (self.CurrentMode == ModeNotes):
                        self.CutPlayingNotes()
                        self.KeyOffset = utils.Limited(self.KeyOffset - 12, 12, 96)
                        self.ClearBtnMap()
                        self.note_mode_handler.Refresh()
                        self.DisplayTimedText('Octave: ' + self.note_mode_handler.GetOctaveRangeText())
                    elif (event.midiId == MIDI_NOTEON) & (patterns.patternNumber() < patterns.patternMax()) & ((self.CurrentMode == ModeStepSeq) | (self.CurrentMode == ModeDrum)):
                        if not self.AltHeld:
                            patterns.jumpToPattern(patterns.patternNumber() + 1)
                        else:
                            patterns.findFirstNextEmptyPat(FFNEP_DontPromptName)
                    elif self.CurrentMode == ModePerf:
                        if self.ShiftHeld:
                            ofsIncrement = 1
                        else:
                            ofsIncrement = 4
                        if (event.midiId == MIDI_NOTEON):
                            self.SetOfs(self.GetTrackOfs() + ofsIncrement, self.GetClipOfs())
                        playlist.lockDisplayZone(1 + self.GetTrackOfs(), event.data2 > 0)

                    self.SendCC(IDPatternDown, int(event.midiId == MIDI_NOTEON) * SingleColorFull)

                elif event.data1 in [IDBankL, IDBankR]:

                    self.GridUpBtnHeld = (event.midiId == MIDI_NOTEON) & (event.data1 == IDBankL)
                    self.GridDownBtnHeld = (event.midiId == MIDI_NOTEON) & (event.data1 == IDBankR)
                    if event.data1 == IDBankL:
                        m = -1
                    else:
                        m = 1
                    if (event.midiId == MIDI_NOTEON):
                        if self.AltHeld:
                            transport.globalTransport(FPT_WindowJog, m, PME_System | PME_FromMidi)
                        elif self.BrowserMode:
                            if (event.data1 == IDBankL):
                                if ui.isInPopupMenu() == 1:
                                  ui.closeActivePopupMenu()
                                else:
                                  ui.navigateBrowserMenu(FPT_Left, self.ShiftHeld)
                            elif (event.data1 == IDBankR):
                                if ui.isInPopupMenu() == 1:
                                  ui.previewBrowserMenuItem()
                                else:
                                  ui.navigateBrowserMenu(FPT_Right, self.ShiftHeld)

                        elif (self.CurrentMode == ModeStepSeq) & (len(self.HeldPads) >= 1):
                            # StepSeq: hold pad + Grid = step shift (special interactive case)
                            general.saveUndo('Fire: Change step shift', UF_PR)
                            HandleHeldPadsParam(m, pShift)
                            p = self.HeldPads[0] - (self.HeldPads[0] // PadsStride) * PadsStride
                            chNum = self.GetChannelNumForPad(self.HeldPads[0])

                            if ui.getVisible(widChannelRack) & (chNum > -1):
                                if channels.isGraphEditorVisible(): # Change to the new parameter
                                    channels.showGraphEditor(False, pShift, p, channels.getChannelIndex(chNum), 0)
                                else: # Open the graph editor to the current channel, step & parameter
                                    channels.showGraphEditor(False, pShift, p, channels.getChannelIndex(chNum), 0)

                            self.HeldPadsChanged = True

                        elif self.ShiftHeld:
                            # Shift + Grid L/R = mode-specific functions
                            if self.CurrentMode == ModeStepSeq:
                                ofsIncrement = 16
                                self.SetChanRackStartPos(self.GetChanRackStartPos() + ofsIncrement * m)
                            elif (self.KeyOffset > 0) & (self.CurrentMode == ModeNotes):
                                self.CutPlayingNotes()
                                self.KeyOffset = utils.Limited(self.KeyOffset + 12 * m, 12, 96)
                                self.ClearBtnMap()
                                self.note_mode_handler.Refresh()
                                self.DisplayTimedText('Root note: ' + utils.GetNoteName(self.KeyOffset))
                            elif self.CurrentMode == ModePerf:
                                self.perf_mode_handler.OnBankLR(m)
                            elif self.CurrentMode == ModeStepEdit:
                                txt = self.step_edit_handler.ScrollPitch(m)
                                self.DisplayTimedText(txt)

                        else:
                            # Grid L = Undo, Grid R = Redo (all modes, no modifier)
                            if event.data1 == IDBankL:
                                general.undoUp()
                                self.DisplayTimedText('Undo')
                            else:
                                general.undoDown()
                                self.DisplayTimedText('Redo')

                    self.SendCC(event.data1, int(event.midiId == MIDI_NOTEON) * SingleColorFull)

                # transport
                elif event.data1 == IDPatternSong:
                    if (event.midiId == MIDI_NOTEON):
                        if not self.ShiftHeld:
                            transport.globalTransport(FPT_Loop, 1)
                        else:
                            transport.globalTransport(FPT_Metronome, 1)

                elif event.data1 == IDPlay:
                    if (event.midiId == MIDI_NOTEON):
                        if not self.ShiftHeld:
                            transport.globalTransport(FPT_Play, 1)
                        else:
                            transport.globalTransport(FPT_WaitForInput, 1)

                elif event.data1 == IDStop:
                    if (event.midiId == MIDI_NOTEON):
                        if not self.ShiftHeld:
                            transport.globalTransport(FPT_Stop, 1)
                        else:
                            transport.globalTransport(FPT_CountDown, 1)

                elif event.data1 == IDRec:
                    if (event.midiId == MIDI_NOTEON):
                        if not self.ShiftHeld:
                            transport.globalTransport(FPT_Record, 1)
                        else:
                            transport.globalTransport(FPT_LoopRecord, 1)

                # knobs modes
                elif event.data1 == IDKnobMode - 1:
                    if (event.midiId == MIDI_NOTEON):
                        if self.CurrentMode in [ModeStepSeq, ModeStepEdit]:
                            subMode = self.GetStepSubMode()
                            subMode += 1
                            if subMode > 3:
                                subMode = 0
                            self.SetStepSubMode(subMode)
                        elif self.ShiftHeld:
                            if self.CurrentKnobsMode == KnobsModeChannelRack:
                                self.CurrentKnobsMode = KnobsModeMixer
                            else:
                                self.CurrentKnobsMode = KnobsModeChannelRack
                            self.DisplayTimedText(KnobsModesNamesT[self.CurrentKnobsMode])
                        elif self.AltHeld:
                            if self.CurrentKnobsMode == KnobsModeUser1:
                                self.CurrentKnobsMode = KnobsModeUser2
                            else:
                                self.CurrentKnobsMode = KnobsModeUser1
                            self.DisplayTimedText(KnobsModesNamesT[self.CurrentKnobsMode])
                        else:
                            self.CurrentKnobsMode += 1
                            if self.CurrentKnobsMode > KnobsModeUser2:
                                self.CurrentKnobsMode = KnobsModeChannelRack
                            self.DisplayTimedText(KnobsModesNamesT[self.CurrentKnobsMode])

                # button modes
                elif event.data1 == IDStepSeq:
                    if (event.midiId == MIDI_NOTEON):
                        self.LayoutSelectionMode = False
                        if self.ShiftHeld & self.AltHeld:
                            # Shift + Alt + Step = toggle StepEdit Poly Accord / Mono
                            if (self.CurrentMode == ModeStepEdit) & self.step_edit_handler.AutoChord:
                                # Already in Accord -> return to Mono
                                self.step_edit_handler.ChordMode = False
                                self.step_edit_handler.AutoChord = False
                                self.step_edit_handler.SyncFromChannelRackMono(True)
                                self.step_edit_handler.Refresh()
                                self.DisplayTimedText('StepEdit: MONO')
                            else:
                                self.step_edit_handler.ChordMode = True
                                self.step_edit_handler.AutoChord = True
                                if self.CurrentMode != ModeStepEdit:
                                    self.CurrentMode = ModeStepEdit
                                self.step_edit_handler.Refresh()
                                self.DisplayTimedText('StepEdit: POLY CHORD')
                        elif self.ShiftHeld:
                            # Shift + Step = original Step Seq mode
                            self.CurrentMode = ModeStepSeq
                            self.ShowCurrentPadMode()
                        elif self.AltHeld:
                            # Alt + Step = toggle StepEdit Poly manuel / Mono
                            if (self.CurrentMode == ModeStepEdit) & self.step_edit_handler.ChordMode & (not self.step_edit_handler.AutoChord):
                                # Already in Poly manuel -> return to Mono
                                self.step_edit_handler.ChordMode = False
                                self.step_edit_handler.AutoChord = False
                                self.step_edit_handler.SyncFromChannelRackMono(True)
                                self.step_edit_handler.Refresh()
                                self.DisplayTimedText('StepEdit: MONO')
                            else:
                                self.step_edit_handler.ChordMode = True
                                self.step_edit_handler.AutoChord = False
                                if self.CurrentMode != ModeStepEdit:
                                    self.CurrentMode = ModeStepEdit
                                self.step_edit_handler.Refresh()
                                self.DisplayTimedText('StepEdit: POLY')
                        else:
                            # Step = enter StepEdit Mono, or toggle Edit if already in StepEdit
                            if self.CurrentMode == ModeStepEdit:
                                # Always toggle edit mode regardless of sub-mode
                                editOn = self.step_edit_handler.ToggleEditMode()
                                if editOn:
                                    self.DisplayTimedText('StepEdit: EDIT ON')
                                else:
                                    self.DisplayTimedText('StepEdit: EDIT OFF')
                                self.step_edit_handler.Refresh()
                            else:
                                self.step_edit_handler.ChordMode = False
                                self.step_edit_handler.AutoChord = False
                                self.CurrentMode = ModeStepEdit
                                self.ShowCurrentPadMode()

                elif event.data1 == IDNote:
                    if (event.midiId == MIDI_NOTEON):
                        self.LayoutSelectionMode = False
                        if self.ShiftHeld:
                            transport.globalTransport(FPT_Snap, 1)
                        else:
                            # Note = standard keyboard mode
                            self.NoteColorSet = 0
                            self.CurrentMode = ModeNotes
                            self.ShowCurrentPadMode()

                elif event.data1 == IDDrum:
                    if (event.midiId == MIDI_NOTEON):
                        self.LayoutSelectionMode = False
                        if not self.ShiftHeld:
                            self.CurrentMode = ModeDrum
                            self.ShowCurrentPadMode()
                        else:
                            transport.globalTransport(FPT_TapTempo, 1)

                elif event.data1 == IDPerform:
                    if (event.midiId == MIDI_NOTEON):
                        self.LayoutSelectionMode = False
                        if not self.ShiftHeld:
                            self.OverviewMode = False
                            self.CurrentMode = ModePerf
                            self.ShowCurrentPadMode()
                        elif self.CurrentMode == ModePerf:
                            self.OverviewMode = False
                            self.DisplayTimedText('Performance mode')

                elif event.data1 in [IDKnob1, IDKnob2, IDKnob3, IDKnob4]:
                    if self.ShiftHeld:
                        # turn them into a CC message so they can be ignored when linking
                        event.midiId = MIDI_CONTROLCHANGE
                        event.data2 = 0
                        event.handled = False
                        return

                    # not a big fan of this, as it way too sensitive IMHO
                    elif event.midiId == MIDI_NOTEON:
                        if self.CurrentMode == ModeDrum:
                            # FL Control mode: touch knobs open/close FL windows
                            txt = self.fl_control_handler.HandleKnobTouch(event.data1)
                            if txt:
                                self.DisplayTimedText(txt)
                        elif (len(self.HeldPads) >= 1) & (self.CurrentMode == ModeStepSeq) & (not self.TouchingKnob):
                            self.TouchingKnob = True
                            self.KnobTouched = event.data1
                            param = -1
                            if event.data1 == IDKnob1:
                                param = pVelocity
                            elif event.data1 == IDKnob2:
                                param = pPan
                            elif event.data1 == IDKnob3:
                                param = pModX
                            elif event.data1 == IDKnob4:
                                param = pModY

                            if len(self.HeldPads) > 0:
                                p = self.HeldPads[0] - (self.HeldPads[0] // PadsStride) * PadsStride
                                chNum = self.GetChannelNumForPad(self.HeldPads[0])

                                if ui.getVisible(widChannelRack) & (chNum > -1) & (param >= 0):
                                    if channels.isGraphEditorVisible(): # Change to the new parameter
                                        channels.showGraphEditor(False, param, p, channels.getChannelIndex(chNum), 0)
                                    else: # Open the graph editor to the current channel, step & parameter
                                        channels.showGraphEditor(False, param, p, channels.getChannelIndex(chNum), 0)

                                self.UHP = general.getUndoHistoryPos()
                                self.UHC = general.getUndoHistoryCount()
                                self.UHL = general.getUndoHistoryLast()
                                self.ChangeFlag = False
                                general.saveUndo('Fire: Change ' + ParamNames[param], UF_PR, True)

                    elif self.KnobTouched == event.data1:
                        self.TouchingKnob = False
                        if self.ChangeFlag:
                            self.ChangeFlag = False
                        else:
                            general.setUndoHistoryPos(self.UHP)
                            general.setUndoHistoryCount(self.UHC)
                            general.setUndoHistoryLast(self.UHL)

            event.handled = True

    def ScaleColor(self, ScaleValue, h, s, v):

        s = min(1.0, (s * 2) * (self.FLFirePadSaturation / 128))
        v = (v * ScaleValue) * (self.FLFirePadBrightness / 128)
        if v > 0.0:
            v = max(v, 0.1)
        r, g, b = utils.HSVtoRGB(h, s, v)
        result = (round((r * 255) - RoundAsFloorS) << 16) + (round((g * 255) - RoundAsFloorS) << 8) + (round((b * 255) - RoundAsFloorS))
        return result, h, s, v

    def OnRefresh(self, Flags):
        self.RefreshTransport()

    def AddPadDataCol(self, dataOut, x, y, Color):
        if self.BtnMap[x + y * PadsStride] == Color:
            return
        r = ((Color >> 16) & 0xFF) // 2
        b = (Color & 0xFF) // 2
        g = ((Color >> 8) & 0xFF) // 2
        dataOut.append(x + y * PadsStride)
        dataOut.append(utils.Limited(r, 0, 0x7F))
        dataOut.append(utils.Limited(g, 0, 0x7F))
        dataOut.append(utils.Limited(b, 0, 0x7F))
        self.BtnMap[x + y * PadsStride] = Color

    def RefreshAnalyzerMode(self):

        BtnMapTemp = [0] * 64

        def GetAnalyzerBars(): #todo

            bandsSrcL = 0
            #if ScopeVisMode == 2:
            #    LockMixThread()
            #    if Assigned(MainForm.MixScope.WAVSample):
            #        bandsSrcL = MixScopeBandsL
            #        if not Assigned(MixScopeBands) | (bandsSrcL < 0):
            #            bandsSrcL = 0
            #        if bandsSrcL > 0:
            #bandsSrcL = utils.Limited(bandsSrcL, 1, 512)
            #            Setlen(bandsSrc, bandsSrcL)
            #            IppsCopy_32F(MixScopeBands, @bandsSrc[0], bandsSrcL)

            #    UnlockMixThread()

            bandsDstL = PadsW
            bandsDst = [0] * bandsDstL
            for i in range(0, bandsDstL - 1):
                bandsDst[i] = 0.0
            if bandsSrcL > 0:
                if bandsSrcL > bandsDstL:
                    bandSrcStep = 1
                    bandDstStep = bandsDstL / bandsSrcL
                else:
                    bandDstStep = 1
                    bandSrcStep = bandsSrcL / bandsDstL

                bandSrc = 0
                bandDst = 0
                mx = 0
                while (bandSrc < bandsSrcL) & (bandDst < bandsDstL):
                    i = utils.Limited(round(bandSrc - RoundAsFloorS), 0, bandsSrcL - 1)
                    mx = utils.max(mx, bandsSrc[i])
                    i2 = utils.Limited(round(bandDst - RoundAsFloorS), 0, bandsDstL - 1)
                    bandsDst[i2] = utils.max(bandsDst[i2], mx)
                    if utils.Limited(round((bandDst + bandDstStep) - RoundAsFloorS), 0, bandsDstL - 1) != i:
                        mx = 0.0
                    bandSrc = bandSrc + bandSrcStep
                    bandDst = bandDst + bandDstStep

            for x in range(0, PadsW):
                mx = utils.Limited((bandsDst[x] * 1) - 0.0, 0.0, 1.0)
                if mx < 0.1:
                    i = -1
                elif (mx < 0.50):
                    i = 0
                elif (mx < 0.70):
                    i = 1
                elif (mx < 0.90):
                    i = 2
                else:
                    i = 3
                for y in range(0, PadsH):
                    padNum = (((PadsH - 1) - y) * PadsW) + x
                    if y > i:
                        c = bgColor
                    else:
                        c = rowColors[y]
                    BtnMapTemp[padNum] = c

        def GetPeakVol(section):

            mx = 0
            if (general.getVersion() > 8):
              mx = mixer.getLastPeakVol(section)
            mx = utils.Limited(mx * 1, 0.0, 1.0) * (PadsH - 1)
            i = round(mx - RoundAsFloorS)
            x = 0
            h = self.AnalyzerHue
            s = 1.0
            v = 1.0
            res, h, s, v = self.ScaleColor(1.0, h, s, v)
            c1 = (res & 0xFEFEFE) >> 1
            res, h, s, v = self.ScaleColor(0.25, h, s, v)
            c2 = (res & 0xFEFEFE) >> 1
            for y in range(0, PadsH):
                padNum = (((PadsH - 1) - y) * PadsW) + x
                if y > i:
                    c = bgColor
                elif y == i:
                    c = c1
                else:
                    c = c2
                BtnMapTemp[padNum] = c

        def ScrollBarsX():

            for y in range(0, PadsH):
                for x in reversed(range(1, PadsW)):
                    BtnMapTemp[(PadsW * y) + x] = BtnMapTemp[(PadsW * y) + x - 1]
                BtnMapTemp[(PadsW * y) + 0] = 0

        def ScrollBarsY():

            for y in range(1, PadsH):
                for x in range(0, PadsW):
                    BtnMapTemp[(PadsW * (y - 1)) + x] = BtnMapTemp[(PadsW * y) + x]

            for x in range(0, PadsW):
                BtnMapTemp[(PadsW * (PadsH - 1) + x)] = 0

        def FlipBarsX():

            for y in range(0, PadsH):
                for x in range(0, (PadsW // 2)):
                    c = BtnMapTemp[(PadsW * y) + x]
                    BtnMapTemp[(PadsW * y) + x] = BtnMapTemp[(PadsW * y) + ((PadsW - 1) - x)]
                    BtnMapTemp[(PadsW * y) + ((PadsW - 1) - x)] = c

        def FlipBarsY():
            for x in range(0, PadsW):
                for y in range(0, (PadsH // 2)):
                    c = BtnMapTemp[(PadsW * y) + x]
                    BtnMapTemp[(PadsW * y) + x] = BtnMapTemp[(PadsW * (PadsH - 1 - y)) + x]
                    BtnMapTemp[(PadsW * (PadsH - 1 - y)) + x] = c

    #***
        if not device.isAssigned():
            return

        bgColor = 0x000000
        rowColors = [0] * PadsH

        for i in range(0, PadsH):
            if (i + 5) <= len(self.KeyColors[self.NoteColorSet]):
                c = (self.KeyColors[self.NoteColorSet][i + 5])
                h, s, v = utils.RGBToHSVColor(c)
                res, h, s, v = self.ScaleColor(1.0, h, s, v)
                c = (res & 0xFEFEFE) >> 1
            rowColors[i] = c

        for padNum in range(0, len(BtnMapTemp)):
            BtnMapTemp[padNum] = self.BtnMap[padNum]

        if self.AnalyzerFlipX:
            FlipBarsX()

        if self.analyzerFlipY:
            FlipBarsY()

        if self.AnalyzerScrollX:
            ScrollBarsX()

        if self.AnalyzerScrollY:
            ScrollBarsY()

        if self.AnalyzerMode == AnalyzerBars:
            GetAnalyzerBars()

        if self.AnalyzerMode == AnalyzerPeakVol:
            GetPeakVol(self.AnalyzerChannel)

        if self.AnalyzerFlipX:
            FlipBarsX()

        if self.analyzerFlipY:
            FlipBarsY()

        dataOut = bytearray((PadsW * PadsH * 4) + 16)
        lenP = 0

        for padNum in range(0, len(BtnMapTemp)):
            if ((BtnMapTemp[padNum] & 0xFF000000) != 0) | (BtnMapTemp[padNum] != self.BtnMap[padNum]):
                if ((BtnMapTemp[padNum] & 0xFF000000) != 0):
                    BtnMapTemp[padNum] = 0
                self.BtnMap[padNum] = BtnMapTemp[padNum]
                lenP += 4
                dataOut[lenP - 4] = padNum
                c = self.BtnMap[padNum]
                dataOut[lenP - 3] = (c & 0x7F0000) >> 16
                dataOut[lenP - 2] = (c & 0x007F00) >> 8
                dataOut[lenP - 1] = (c & 0x00007F) >> 0

        if (lenP > 0):
            dataOut = dataOut[: lenP]  #todo check if needed
            self.SendMessageToDevice(MsgIDSetRGBPadLedState, lenP, dataOut)

    def RefreshTransport(self):

        if (not device.isAssigned()) | self.ShiftHeld:
            return

        if transport.isPlaying() == PM_Playing:
            val = DualColorFull1
            val2 = SingleColorHalfBright
        else:
            val = DualColorHalfBright2
            val2 = SingleColorOff

        if (transport.isPlaying() != PM_Playing) & (not self.ShiftHeld): #donn't update during playback, it's already handled by UpdateBeatIndicator
            self.SendCC(IDPlay, val)
        self.SendCC(IDStop, val2)
        if transport.isRecording():
            val = DualColorFull1
        else:
            val = DualColorHalfBright2
        self.SendCC(IDRec, val)
        if transport.getLoopMode() == SM_Pat:
            val = DualColorFull2
        else:
            val = DualColorFull1
        self.SendCC(IDPatternSong, val)

    def SendCC(self, ID, Val):

        if (not device.isAssigned()):
            return
        device.midiOutNewMsg(MIDI_CONTROLCHANGE + (ID << 8) + (Val << 16), ID)

    def SendMessageToDevice(self, ID, l, data):

        if not device.isAssigned():
            return
        
        msg = bytearray(7 + l + 1)
        lsb = l & 0x7F
        msb = (l & (~ 0x7F)) >> 7

        msg[0] = MIDI_BEGINSYSEX
        msg[1] = ManufacturerIDConst
        msg[2] = DeviceIDBroadCastConst
        msg[3] = ProductIDConst
        msg[4] = ID
        msg[5] = msb
        msg[6] = lsb
        if (l > 63):
            for n in range(0, len(data)):
                msg[7 + n] = data[n]
        else:
            for n in range(0, l):
                msg[7 + n] = data[n]
        msg[len(msg) - 1] = MIDI_ENDSYSEX
        device.midiOutSysex(bytes(msg))
        
    def DispatchMessageToDeviceScripts(self, ID, data1, data2, data3):

        if not device.isAssigned():
            return

        l = 6
        data = bytearray(l)
               
        data[0] = data1 & 0x7F
        data[1] = (data1 & (~ 0x7F)) >> 7
        data[2] = data2 & 0x7F
        data[3] = (data2 & (~ 0x7F)) >> 7
        data[4] = data3 & 0x7F
        data[5] = (data3 & (~ 0x7F)) >> 7          
        
        msg = bytearray(7 + l + 1)
        lsb = l & 0x7F
        msb = (l & (~ 0x7F)) >> 7

        msg[0] = MIDI_BEGINSYSEX
        msg[1] = ManufacturerIDConst
        msg[2] = DeviceIDBroadCastConst
        msg[3] = ProductIDConst
        msg[4] = ID
        msg[5] = msb
        msg[6] = lsb
        if (l > 63):
            for n in range(0, len(data)):
                msg[7 + n] = data[n]
        else:
            for n in range(0, l):
                msg[7 + n] = data[n]
        msg[len(msg) - 1] = MIDI_ENDSYSEX
        device.dispatch(-1, 0xF4, bytes(msg))

    def SetAsMasterDevice(self, Value):
    
        receiverCount = device.dispatchReceiverCount()
        otherDeviceFound = receiverCount > 0 

        if (not otherDeviceFound) & Value:
            return # no need to switch to master if there's only one device
        if Value == True:
            self.MultiDeviceMode = MultiDev_Master
            self.StepEditDeviceIndex = 0  # master is always device 0
        else:
            self.MultiDeviceMode = MultiDev_Single
            self.StepEditDeviceIndex = 0
        self.MasterDevice = -1
        
        if Value:        
            self.DispatchMessageToDeviceScripts(SM_SetAsSlave, device.getPortNumber(), 0, 0)
            self.DispatchMessageToDeviceScripts(SM_MasterDeviceChanRackOfs, self.ChanRackOfs, 0, 0)
            self.DispatchMessageToDeviceScripts(SM_MasterDeviceChanStartPos, self.ChanRackStartPos, 0, 0)
        else:
            self.DispatchMessageToDeviceScripts(SM_SetAsSingle, device.getPortNumber(), 0, 0)
            self.SetAsSingleDevice 
                    
        if Value:
            self.DisplayTimedText('Multi-device')
        else:
            self.DisplayTimedText('Single device')

    def SetAsSingleDevice(self):

        self.MultiDeviceMode = MultiDev_Single
        self.StepEditDeviceIndex = 0
        self.MasterDevice = -1
        self.SlavedDevices = {}
        self.SlaveLayoutSelectionMode = False
        self.DisplayTimedText('Single device')

    def SetAsSlaveDevice(self, Master):

        self.MultiDeviceMode = MultiDev_Slave
        self.MasterDevice = Master  #master device port number
        self.SlavedDevices = {}
        self.SlaveLayoutSelectionMode = True # so the slave layout selection menu shows up immediately on the slaved device
        # Step edit device index is set when layout is confirmed (see UpdateSlaveStepEditIndex)
        self.UpdateSlaveStepEditIndex()
        self.DisplayTimedText(SlaveModeLayoutNamesT[self.SlaveModeLayout])

    def UpdateSlaveStepEditIndex(self):
        """Update StepEditDeviceIndex for step edit sync.
        Right layout: slave index=1 (shows steps 5-8, master shows 1-4).
        Left layout: slave index=0 (shows steps 1-4, master shows 5-8)."""
        if self.SlaveModeLayout == SlaveModeLayout_Left:
            self.StepEditDeviceIndex = 0  # slave is left = shows first steps
        else:
            self.StepEditDeviceIndex = 1  # slave is right = shows next steps
        # If already in Step Edit mode, apply offset now
        if self.CurrentMode == ModeStepEdit:
            try:
                self.step_edit_handler.ApplyMultiDeviceOffset()
            except Exception:
                pass

    def Sign(self, Value):
        if Value >= 0: 
            return 1
        else: 
            return -1

    def SetChanRackOfs(self, Value, Dispatch = True):

        if self.MultiDeviceMode != MultiDev_Slave:
            self.ChanRackOfs = utils.Limited(Value, 0, channels.channelCount() - 1)
            if Dispatch:
              self.DispatchMessageToDeviceScripts(SM_MasterDeviceChanRackOfs, self.ChanRackOfs, 0, 0)

            if ui.getVisible(widChannelRack):
                R = self.GetGridRect(ModeStepSeq)
                ui.crDisplayRect(R.Left, R.Top, R.Right, R.Bottom, 2000)
        else:  #slave to master
            if Dispatch:
                self.DispatchMessageToDeviceScripts(SM_SlaveDeviceRackOfs, Value - self.GetChanRackOfs() + 128, 0, 0)
                self.MasterDeviceChanRackOfs = max(self.MasterDeviceChanRackOfs + Value - self.GetChanRackOfs(), 0)

        self.DisplayTimedText('Channels ' + str(self.GetChanRackOfs() + 1) + '-' + str(self.GetChanRackOfs() + 4))

    def SetChanRackStartPos(self, Value, Dispatch = True):

        if self.MultiDeviceMode != MultiDev_Slave:
            self.ChanRackStartPos = utils.Limited(Value, 0, patterns.patternMax() - 16) # TODO check slaves for bounds

            self.DispatchMessageToDeviceScripts(SM_MasterDeviceChanStartPos, self.ChanRackStartPos, 0, 0)
            
            if ui.getVisible(widChannelRack):
                R = self.GetGridRect(ModeStepSeq)
                ui.crDisplayRect(R.Left, R.Top, R.Right, R.Bottom, 2000)
        else:   #slave to master
            if Dispatch:
                self.DispatchMessageToDeviceScripts(SM_SlaveDeviceStartPos, Value - self.GetChanRackStartPos() + 128, 0, 0)

        self.DisplayTimedText('Grid offset: ' + str(self.GetChanRackStartPos()))

    def SetOfs(self, TrackOfsValue, ClipOfsValue, Dispatch= True):

        oTOfs = self.TrackOfs
        oCOfs = self.ClipOfs
        if self.CurrentMode == ModePerf:
            if self.MultiDeviceMode != MultiDev_Slave:      # is master
                self.TrackOfs = utils.Limited(TrackOfsValue, 0, playlist.trackCount() - PadsH)
                R = self.GetGridRect(self.CurrentMode)
                pw = R.Width()

                n = playlist.liveTimeToBlockNum(max(playlist.getSongStartTickPos() - 1, 0))
                self.ClipOfs = utils.Limited(ClipOfsValue, 0, max(n - (pw - 1), 0))

                if Dispatch: # dispatch to slave
                  self.DispatchMessageToDeviceScripts(SM_MasterDeviceSetOfs, self.TrackOfs + 128, self.ClipOfs + 128, 0)

            else:  # is slave
                if Dispatch:  # dispatch to master
                  self.DispatchMessageToDeviceScripts(SM_SlaveDeviceSetOfs, TrackOfsValue - self.GetTrackOfs() + 128, ClipOfsValue - self.GetClipOfs() + 128, 0)
                  self.DispatchMessageToDeviceScripts(SM_UpdateLiveMode, 0, 0, 0)
                  self.OnUpdateLiveMode(1, playlist.trackCount())
                  return

            if device.isAssigned():
                self.OnUpdateLiveMode(1, playlist.trackCount())

            if playlist.getDisplayZone() != 0:
                # Get the actual displayed rectangle so we can compare it to the current view
                R = utils.TRect(playlist.liveBlockNumToTime(self.ClipOfs), self.TrackOfs, playlist.liveBlockNumToTime(self.ClipOfs + PadsW - 1), self.TrackOfs + PadsH - 1)
                if oCOfs > self.ClipOfs: # User moved selection left
                    playlist.scrollTo(0, R.Left)
                elif oCOfs < self.ClipOfs: # User moved selection right
                    playlist.scrollTo(1, R.Left, R.Right)
                elif oTOfs < self.TrackOfs: # User moved down
                    R.Bottom = min(R.Bottom + 1, playlist.trackCount() - PadsH)
                    playlist.scrollTo(2, 0, 0, R.Bottom)
                elif oTOfs > self.TrackOfs: # User moved up
                    R.Top = min(R.Top + 1, playlist.trackCount() - PadsH)
                    playlist.scrollTo(3, 0, 0, R.Top)

                self.OnDisplayZone()

    def SetStepParam(self, Step, Param, Value):
        index = channels.channelNumber()
        if index < 0:
            return
        stepPos = self.step_seq_handler.PadToStep(Step)
        if channels.getGridBit(index, stepPos) == 0:
            channels.setGridBit(index, stepPos, 1) # make sure the step is enabled | it won't work !
        channels.setStepParameterByIndex(channels.getChannelIndex(index), patterns.patternNumber(), stepPos, Param, Value, 1)

    def SetStepSubMode(self, subMode):

        if subMode == 0:
            self.step_edit_handler.ChordMode = False
            self.step_edit_handler.AutoChord = False
            self.CurrentMode = ModeStepSeq
            self.ShowCurrentPadMode()
        elif subMode == 1:
            self.step_edit_handler.ChordMode = False
            self.step_edit_handler.AutoChord = False
            if self.CurrentMode != ModeStepEdit:
                self.CurrentMode = ModeStepEdit
            self.step_edit_handler.SyncFromChannelRackMono(True)
            self.step_edit_handler.Refresh()
            self.DisplayTimedText('StepEdit: MONO')
        elif subMode == 2:
            self.step_edit_handler.ChordMode = True
            self.step_edit_handler.AutoChord = False
            if self.CurrentMode != ModeStepEdit:
                self.CurrentMode = ModeStepEdit
            self.step_edit_handler.Refresh()
            self.DisplayTimedText('StepEdit: POLY')
        elif subMode == 3:
            self.step_edit_handler.ChordMode = True
            self.step_edit_handler.AutoChord = True
            if self.CurrentMode != ModeStepEdit:
                self.CurrentMode = ModeStepEdit
            self.step_edit_handler.Refresh()
            self.DisplayTimedText('StepEdit: POLY CHORD')

    def GetStepSubMode(self):

        if self.CurrentMode == ModeStepSeq:
            return 0
        if self.step_edit_handler.AutoChord:
            return 3
        if self.step_edit_handler.ChordMode:
            return 2
        return 1

    def ShowCurrentPadMode(self):

        if self.CurrentMode < len(ModeNamesT):
            self.DisplayTimedText(ModeNamesT[self.CurrentMode])
        elif self.CurrentMode == ModeChordSelect:
            self.DisplayTimedText('Chord select mode')
        else:
            self.DisplayTimedText('Mode ' + str(self.CurrentMode))

    def OnUpdateBeatIndicator(self, Value):

        dataOut = bytearray(0)
        if not device.isAssigned():
            return
        if Value == 0:
            val = 0
        elif Value == 1:
            val = DualColorFull2
        elif Value == 2:
            val = DualColorFull1
        else:
            val = 0

        if not self.ShiftHeld:
            self.SendCC(IDPlay, val)

        for n in range(0, len(self.PlayingPads)):
          if Value > 0:
            self.AddPadDataCol(dataOut, self.PlayingPads[n][0], self.PlayingPads[n][1], self.PlayingPads[n][2])
          else:
            self.AddPadDataCol(dataOut, self.PlayingPads[n][0], self.PlayingPads[n][1], 0)

        if len(dataOut) > 0:
            screen.unBlank(True)
            self.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)

        # Dispatch beat indicator to active mode
        if self.CurrentMode == ModeNotes:
            self.note_mode_handler.OnUpdateBeatIndicator(Value)
        elif self.CurrentMode == ModeDrum:
            self.drum_mode_handler.OnUpdateBeatIndicator(Value)
        elif self.CurrentMode == ModePerf:
            self.perf_mode_handler.OnUpdateBeatIndicator(Value)

    def UpdateCurrentKnobsMode(self):

        if not device.isAssigned():
            return
        val = 0
        if self.CurrentMode == ModeStepSeq:
            val = 1
        elif self.CurrentMode == ModeStepEdit:
            if self.step_edit_handler.AutoChord:
                val = 8
            elif self.step_edit_handler.ChordMode:
                val = 4
            else:
                val = 2
        elif self.CurrentKnobsMode == KnobsModeChannelRack:
            val = 1
        elif self.CurrentKnobsMode == KnobsModeMixer:
            val = 2
        elif self.CurrentKnobsMode == KnobsModeUser1:
            val = 4
        elif self.CurrentKnobsMode == KnobsModeUser2:
            val = 8

        val = val | 16 # enable bit control of led states

        # knob mode led
        self.SendCC(IDKnobMode, val)
        # Shift/Alt LEDs are managed by UpdateCurrentModeBtns in StepEdit mode
        if self.CurrentMode == ModeStepEdit:
            pass  # don't overwrite Shift/Alt LEDs here
        else:
            self.SendCC(IDShift, int(self.ShiftHeld) * SingleColorFull)
            self.SendCC(IDAlt, int(self.AltHeld) * SingleColorFull)
        if self.CurrentMode == ModeChordSelect:
            self.SendCC(IDBrowser, DualColorFull1)  # red for chord select
        else:
            self.SendCC(IDBrowser, int(self.BrowserMode) * SingleColorFull)

    def AdaptKnobVal(self, Value):

        return Value # signof(Value) to ignore acceleartion

    def AdaptVelocity(self, Value):

        if not self.AccentMode & (Value > 0):
            Value = 100
        elif self.AccentMode & (Value > 0):

            if Value < 64:
                Value = 100
            else:
                Value = 127
        return Value

    def CheckForMasterDevice(self):

        if self.MultiDeviceMode != MultiDev_Slave:
            return # we're not slaved to another device, no need to check for a master
        for n in range(0, len(MIDIInDevices)):
            if (MidiInDevices[n] is TMIDIInDevice_Fire) & (MidiInDevices[n] != Self) & (TMidiInDevice_Fire(MidiInDevices[n]).IsMasterDevice):
                self.MasterDevice = TMidiInDevice_Fire(MidiInDevices[n])

    def ClearAllButtons(self):

        # pads modes
        self.SendCC(IDStepSeq, SingleColorOff)
        self.SendCC(IDNote, SingleColorOff)
        self.SendCC(IDDrum, SingleColorOff)
        self.SendCC(IDPerform, SingleColorOff)
        # knobs modes
        self.SendCC(IDKnobMode, 16)
        # shift button
        self.SendCC(IDShift, SingleColorOff)
        # Alt button
        self.SendCC(IDAlt, SingleColorOff)
        # mute buttons
        self.SendCC(IDMute1, SingleColorOff)
        self.SendCC(IDMute2, SingleColorOff)
        self.SendCC(IDMute3, SingleColorOff)
        self.SendCC(IDMute4, SingleColorOff)
        # track select buttons
        self.SendCC(IDTrackSel1, SingleColorOff)
        self.SendCC(IDTrackSel2, SingleColorOff)
        self.SendCC(IDTrackSel3, SingleColorOff)
        self.SendCC(IDTrackSel4, SingleColorOff)
        # transport buttons
        self.SendCC(IDPlay, SingleColorOff)
        self.SendCC(IDStop, SingleColorOff)
        self.SendCC(IDRec, SingleColorOff)
        self.SendCC(IDPatternSong, SingleColorOff)
        # browser button
        self.SendCC(IDBrowser, SingleColorOff)
        # grid
        self.SendCC(IDBankL, SingleColorOff)
        self.SendCC(IDBankR, SingleColorOff)
        # patterns
        self.SendCC(IDPatternUp, SingleColorOff)
        self.SendCC(IDPatternDown, SingleColorOff)

    def ClearAllPads(self):

        dataOut = bytearray(64 * 4)
        i = 0
        for n in range(0, 64):
            dataOut[i] = n
            dataOut[i + 1] = 0
            dataOut[i + 2] = 0
            dataOut[i + 3] = 0
            i += 4

        self.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)
        time.sleep(0.1) # brief wait for device to process

    def ClearBtnMap(self):

        for n in range(0, 64):
            self.BtnMap[n] = -1
        self.OldNoteMode = -1 # make sure we refresh notes mode

    def ClearDisplayText(self):

        dataOut = bytearray(3)

        dataOut[0] = 0
        dataOut[1] = 0
        for n in range(0, 8):
            dataOut[2] = n
            self.SendMessageToDevice(MsgIDDrawScreenText, len(dataOut), dataOut)

    def ClearDisplay(self):

        screen.fillRect(0, 0, self.DisplayWidth, self.DisplayHeight, self.BgCol)
        screen.update()

    def ClearHeldPads(self):

        self.HeldPads = bytearray()

    def ClearKnobsMode(self):

        self.SendCC(IDKnobMode, 16)

    def UpdateCurrentModeBtns(self):

        if not device.isAssigned():
            return
        self.BtnT[IdxStepSeq] = int(self.CurrentMode == ModeStepSeq)
        self.BtnT[IdxNote] = int(self.CurrentMode == ModeNotes)
        self.SendCC(IDNote, self.BtnT[IdxNote] * SingleColorFull)
        if self.CurrentMode == ModeChordSelect:
            self.SendCC(IDBrowser, DualColorFull1)  # red for chord select
        else:
            self.SendCC(IDBrowser, int(self.BrowserMode) * SingleColorFull)
        self.BtnT[IdxDrum] = int(self.CurrentMode == ModeDrum)
        self.BtnT[IdxPerform] = int(self.CurrentMode == ModePerf)
        if self.CurrentMode == ModeStepSeq:
            self.SendCC(IDStepSeq, DualColorFull1)  # red for classic StepSeq
        else:
            self.SendCC(IDStepSeq, self.BtnT[IdxStepSeq] * SingleColorFull)
        self.SendCC(IDDrum, self.BtnT[IdxDrum] * SingleColorFull)
        self.SendCC(IDPerform, self.BtnT[IdxPerform] * SingleColorFull)

        if False:
            if self.BlinkTimer >= BlinkSpeed:
                self.SendCC(IDPerform, SingleColorOff)
            else:
                self.SendCC(IDPerform, SingleColorFull)

        if self.CurrentMode == ModeStepSeq:
            # TrackSel LEDs off in classic StepSeq (step_seq handles mute/sel state)
            for i in range(4):
                self.SendCC(IDTrackSel1 + i, SingleColorOff)

        if self.CurrentMode == ModeStepEdit:
            # Pattern Up/Down red in StepEdit modes
            self.SendCC(IDPatternUp, DualColorFull1)
            self.SendCC(IDPatternDown, DualColorFull1)
            if self.step_edit_handler.EditMode:
                # Blink StepSeq button when edit mode is active
                if self.BlinkTimer >= BlinkSpeed:
                    self.SendCC(IDStepSeq, SingleColorOff)
                else:
                    self.SendCC(IDStepSeq, SingleColorFull)
            else:
                self.SendCC(IDStepSeq, SingleColorFull)

            if self.step_edit_handler.AutoChord:
                # Poly Accord: Shift red + Alt orange
                self.SendCC(IDShift, DualColorFull1)
                self.SendCC(IDAlt, DualColorFull2)
            elif self.step_edit_handler.ChordMode:
                # Poly manuel: Alt orange only
                if not self.ShiftHeld:
                    self.SendCC(IDShift, SingleColorOff)
                self.SendCC(IDAlt, DualColorFull2)
            else:
                # Mono: normal LED state
                if not self.ShiftHeld:
                    self.SendCC(IDShift, SingleColorOff)
                if not self.AltHeld:
                    self.SendCC(IDAlt, SingleColorOff)

            # TrackSel LEDs = sub-mode indicator
            # LED1 = StepSeq classique (Shift+Step)
            # LED2 = StepEdit Mono
            # LED3 = StepEdit Poly
            # LED4 = StepEdit Poly Accords
            isClassicStepSeq = False  # we're in ModeStepEdit, not ModeStepSeq
            isMono = not self.step_edit_handler.ChordMode and not self.step_edit_handler.AutoChord
            isPoly = self.step_edit_handler.ChordMode and not self.step_edit_handler.AutoChord
            isAutoChord = self.step_edit_handler.AutoChord
            self.SendCC(IDTrackSel1, SingleColorFull if isClassicStepSeq else SingleColorOff)
            self.SendCC(IDTrackSel2, SingleColorFull if isMono else SingleColorOff)
            self.SendCC(IDTrackSel3, SingleColorFull if isPoly else SingleColorOff)
            self.SendCC(IDTrackSel4, SingleColorFull if isAutoChord else SingleColorOff)

    def UpdateCurrentPadsMode(self):

        if self.CurrentMode != self.OldMode:
            # Deactivate previous mode if needed
            if self.OldMode == ModeStepEdit:
                self.step_edit_handler.OnDeactivate()
            elif self.OldMode == ModePerf:
                self.perf_mode_handler.OnDeactivate()
            elif self.OldMode == ModeDrum:
                self.drum_mode_handler.OnDeactivate()
                self.fl_control_handler.OnDeactivate()
            elif self.OldMode == ModeNotes:
                self.note_mode_handler.OnDeactivate()
            self.ClearBtnMap()
            self.CutPlayingNotes()
            self.ClearHeldPads()
            # automatically return submodes when switch pad modes
            self.LayoutSelectionMode = False
            self.BrowserMode = False
            self.AccentMode = False
            self.OverviewMode = False
            self.MixerTrackSelectionMode = False
            channels.closeGraphEditor(True)

        if self.CurrentMode == ModeStepSeq:
            self.step_seq_handler.Refresh(False)
        elif self.CurrentMode == ModeNotes:
            if self.CurrentMode != self.OldMode:
                self.note_mode_handler.OnActivate()
            self.note_mode_handler.Refresh()
        elif self.CurrentMode == ModeDrum:
            if self.CurrentMode != self.OldMode:
                self.drum_mode_handler.OnActivate()
                self.fl_control_handler.OnActivate()
            else:
                self.fl_control_handler.Refresh()
        elif self.CurrentMode in [ModeAnalyzerLeft, ModeAnalyzerRight, ModeAnalyzerMono]:
            self.RefreshAnalyzerMode()
        elif self.CurrentMode == ModePerf:
            if self.CurrentMode != self.OldMode:
                self.perf_mode_handler.OnActivate()
            else:
                self.perf_mode_handler.Refresh()
        elif self.CurrentMode == ModeStepEdit:
            if self.CurrentMode != self.OldMode:
                self.step_edit_handler.OnActivate()
            else:
                self.step_edit_handler.Refresh()
        elif self.CurrentMode == ModeChordSelect:
            if self.CurrentMode != self.OldMode:
                self.chord_select_handler.OnActivate()
            else:
                self.chord_select_handler.Refresh()
        else:
            self.ClearAllPads() # undefined mode

        self.OldMode = self.CurrentMode

    def OnUpdateLiveMode(self, FirstTrackNum, LastTrackNum):

        if self.CurrentMode == ModePerf:
            self.perf_mode_handler.Refresh() # is it really needed ? idle might already take care of that

    def SetScreenMode(self, mode):

        if self.ScreenMode != mode:

            self.ScreenMode = mode

            i = screen.findTextLine(0, 20, 128, 20 + 44)
            if (general.getVersion() > 8):
              if (i >= 0):
                screen.removeTextLine(i, 1)
              if mode in [ScreenModePeak, ScreenModeScope]:
                screen.addMeter(mode, 0, 20, 128, 20 + 44)

    def SetAnalyzerMode(self, mode):

      self.AnalyzerScrollX = False
      self.AnalyzerScrollY = False
      self.AnalyzerFlipX = False
      self.AnalyzerFlipY = False
      self.AnalyzerChannel = 0
      self.AnalyzerMode = AnalyzerBars
      if mode == ModeAnalyzerLeft:
        self.AnalyzerScrollX = True
        self.AnalyzerFlipX = True
        self.AnalyzerMode = AnalyzerPeakVol
        self.AnalyzerChannel = 0
      elif mode == ModeAnalyzerRight:
        self.AnalyzerScrollX = True
        self.AnalyzerFlipX = False
        self.AnalyzerMode = AnalyzerPeakVol
        self.AnalyzerChannel = 1
      self.ClearBtnMap()

Fire = TFire()

def OnInit():
    Fire.OnInit()

def OnDeInit():
    Fire.OnDeInit()

def OnDisplayZone():
    Fire.OnDisplayZone()

def OnIdle():
    Fire.OnIdle()

def OnMidiIn(event):
    Fire.OnMidiIn(event)

def OnMidiMsg(event):
    Fire.OnMidiMsg(event)

def OnRefresh(Flags):
    Fire.OnRefresh(Flags)

def OnUpdateLiveMode(LastTrackNum):
    Fire.OnUpdateLiveMode(1, LastTrackNum)

def OnUpdateBeatIndicator(Value):
    Fire.OnUpdateBeatIndicator(Value)
