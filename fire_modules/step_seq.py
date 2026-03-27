#   name=AKAI FL Studio Fire - Step Sequencer Mode
#   Logique du mode Step Sequencer

import channels
import general
import patterns
import device
import screen
import ui
import utils
import mixer

from fire_modules.mode_base import FireModeBase
from fire_modules.constants import *
from fire_modules.fire_utils import TMidiEvent


class StepSeqMode(FireModeBase):
    """Gère le mode Step Sequencer : grille de pas, accent, édition de paramètres."""

    def __init__(self, fire_device):
        super().__init__(fire_device)
        self.ParamNames = ('Step pitch', 'Velocity', 'Release', 'Fine pitch', 'Panning', 'Mod X', 'Mod Y', 'Shift')

    # --- Step operations ---

    def PadToStep(self, padNum):
        """Convert pad number (0..63) to absolute step position in 1x64 layout.
        Row 0 (pads 0-15)  = startPos + 0..15
        Row 1 (pads 16-31) = startPos + 16..31
        Row 2 (pads 32-47) = startPos + 32..47
        Row 3 (pads 48-63) = startPos + 48..63
        """
        padRow = padNum // PadsStride
        padCol = padNum - padRow * PadsStride
        return self.fire.GetChanRackStartPos() + padRow * 16 + padCol

    def SetStep(self, padNum, Force):
        Result = False
        index = channels.channelNumber()
        if index < 0:
            return Result
        stepPos = self.PadToStep(padNum)
        general.saveUndo('Fire: Step seq edit', UF_PR, True)
        if self.fire.CurrentMode == ModeStepSeq:
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

    # --- Pad event handling ---

    def HandleStepSeqPad(self, id, padNum):
        tempHeldPads = bytearray()

        # store pads being held
        if id == MIDI_NOTEON:
            self.fire.HeldPads.append(padNum)
        else:
            for i in range(0, len(self.fire.HeldPads)):
                if self.fire.HeldPads[i] != padNum:
                    tempHeldPads.append(self.fire.HeldPads[i])

            self.fire.HeldPads = bytearray(len(tempHeldPads))
            for i in range(0, len(tempHeldPads)):
                self.fire.HeldPads[i] = tempHeldPads[i]

        didSetStep = False
        if id == MIDI_NOTEOFF:
            didSetStep = self.SetStep(padNum, self.fire.HeldPadsChanged) # if we tweaked a param, force the step on upon releasing

        if self.fire.AccentMode & didSetStep:
            self.fire.SetStepParam(padNum, pPitch, self.fire.AccentParams.Pitch)
            self.fire.SetStepParam(padNum, pVelocity, self.fire.AccentParams.Vel)
            self.fire.SetStepParam(padNum, pPan, self.fire.AccentParams.Pan)
            self.fire.SetStepParam(padNum, pModX, self.fire.AccentParams.ModX)
            self.fire.SetStepParam(padNum, pModY, self.fire.AccentParams.ModY)
            channels.updateGraphEditor()

        if len(self.fire.HeldPads) == 0:
            self.fire.HeldPadsChanged = False
            channels.closeGraphEditor(True)

    def OnPadEvent(self, event, pad_num):
        """Gère les pads en mode Step Sequencer."""
        HeldMuteBtn = -1
        for n in range(0, 4):
            if self.fire.MuteBtnStates[n]:
                HeldMuteBtn = n
                break
        if (HeldMuteBtn >= 0):
            y = pad_num // PadsStride
            x = pad_num - y * PadsStride
            if y == HeldMuteBtn:
                self.SetChanLoop(HeldMuteBtn + self.fire.GetChanRackOfs(), x + 1 + self.fire.GetChanRackStartPos())
        else:
            self.HandleStepSeqPad(event.midiId, pad_num)

    # --- Held pads parameter editing ---

    def HandleHeldPadsParam(self, Data2, Param):
        ParamDefVal = (DotNote_Default, 100, 64, 120, 64, 128, 128, 0)
        ParamMax = (127, 127, 127, 240, 127, 255, 255, 255)
        ParamInc = (1, 2, 2, 2, 2, 2, 2, 1)
        RecPPS = mixer.getRecPPS()

        index = channels.channelNumber()
        if index < 0:
            return

        for m in range(0, len(self.fire.HeldPads)):
            stepPos = self.PadToStep(self.fire.HeldPads[m])

            if (Param == pShift) & (channels.getGridBit(index, stepPos) == 0):
                channels.setGridBit(index, stepPos, 1)

            val = self.fire.GetStepParam(self.fire.HeldPads[m], Param)
            oldVal = val

            if val == -1:
                val = ParamDefVal[Param]

            if Data2 >= 0x7F // 2:
                Data2 = -(0x80 - Data2)

            if Data2 > 0:
                val += ParamInc[Param]
            else:
                val -= ParamInc[Param]

            if Param == pShift: # other parameters will be limited by graph editor
                oldVal = (oldVal // RecPPS) * RecPPS
                val = utils.Limited(val, oldVal, oldVal + RecPPS - 1)
            self.fire.SetStepParam(self.fire.HeldPads[m], Param, val)

            if Param != pShift:
                val = utils.Limited(val, 0, ParamMax[Param])

            if m == 0:
                if Param == pPitch:
                    self.fire.DisplayTimedText(self.ParamNames[Param] + ': ' + utils.GetNoteName(val))
                else:
                    if Param == pShift:
                        val = val % RecPPS
                        self.fire.DisplayBar(self.ParamNames[Param] + ': ' + str(val), val / (RecPPS - 1), False)
                    else:
                        bipolar = (Param == pFinePitch) | (Param == pPan)
                        if bipolar:
                            showVal = val - ParamMax[Param] // 2
                        else:
                            showVal = val
                        self.fire.DisplayBar(self.ParamNames[Param] + ': ' + str(showVal), val / ParamMax[Param], bipolar)

            channels.updateGraphEditor()

    def SetChanLoop(self, ChanIndex, LoopLength):
        loopName = patterns.setChannelLoop(ChanIndex, LoopLength)
        self.fire.DisplayTimedText(channels.getChannelName(ChanIndex) + ' loop: ' + loopName)
        self.fire.DidTweakLooping = True

    # --- Jog wheel handling ---

    def OnJogWheel(self, event):
        """Gère le jog wheel en mode Step Seq."""
        if self.fire.MixerTrackSelectionMode:
            m = channels.channelNumber()
            if m < 0:
                return True
            p = channels.getTargetFxTrack(m)
            if event.data2 == 1:
                p += 1
            else:
                p -= 1
            p = utils.Limited(p, 0, mixer.trackCount() - 1)
            general.processRECEvent(channels.getRecEventId(m) + REC_Chan_FXTrack, p, REC_Control | REC_UpdateControl)
            mixer.setTrackNumber(p, curfxScrollToMakeVisible | curfxMinimalLatencyUpdate)
            self.fire.DisplayTimedText('Chan ' + str(m + 1) + chr(13) + 'Track: ' + mixer.getTrackName(channels.getTargetFxTrack(m)))
            return True

        if self.fire.AccentMode:
            if event.data2 == 1:
                self.fire.AccentParams.Pitch += 1
            else:
                self.fire.AccentParams.Pitch -= 1
            self.fire.AccentParams.Pitch = utils.Limited(self.fire.AccentParams.Pitch, 0, 127)
            self.fire.DisplayTimedText('Default pitch : ' + utils.GetNoteName(self.fire.AccentParams.Pitch))
            return True

        # Default: held pads pitch or channel rack scroll
        if len(self.fire.HeldPads) >= 1:
            self.HandleHeldPadsParam(event.data2, pPitch)
            p = self.fire.HeldPads[0] - (self.fire.HeldPads[0] // PadsStride) * PadsStride
            chNum = self.fire.GetChannelNumForPad(self.fire.HeldPads[0])
            if ui.getVisible(widChannelRack) & (chNum > -1):
                channels.showGraphEditor(False, pPitch, p, channels.getChannelIndex(chNum), 0)
            self.fire.HeldPadsChanged = True
            return True

        # Select next/prev channel
        m = channels.selectedChannel()
        if event.data2 == 1:
            m += 1
        else:
            m -= 1
        m = utils.Limited(m, 0, channels.channelCount() - 1)
        channels.selectOneChannel(m)
        if ui.getVisible(widChannelRack):
            R = self.fire.GetGridRect(ModeStepSeq)
            ui.crDisplayRect(R.Left, R.Top, R.Right, R.Bottom, 2000)
        self.fire.DisplayTimedText('Chan: ' + channels.getChannelName(m))
        return True

    def OnBankLR(self, event, m):
        """Gère les boutons Bank L/R en mode Step Seq."""
        if len(self.fire.HeldPads) >= 1:
            general.saveUndo('Fire: Change step shift', UF_PR)
            self.HandleHeldPadsParam(m, pShift)
            p = self.fire.HeldPads[0] - (self.fire.HeldPads[0] // PadsStride) * PadsStride
            chNum = self.fire.GetChannelNumForPad(self.fire.HeldPads[0])
            if ui.getVisible(widChannelRack) & (chNum > -1):
                if channels.isGraphEditorVisible(): # Change to the new parameter
                    channels.showGraphEditor(False, pShift, p, channels.getChannelIndex(chNum), 0)
                else: # Open the graph editor to the current channel, step & parameter
                    channels.showGraphEditor(False, pShift, p, channels.getChannelIndex(chNum), 0)

            self.fire.HeldPadsChanged = True
        else:
            if self.fire.ShiftHeld:
                ofsIncrement = 1
            else:
                ofsIncrement = 16
            self.fire.SetChanRackStartPos(self.fire.GetChanRackStartPos() + ofsIncrement * m)

    # --- Knobs handling for step seq ---

    def HandleKnobs(self, event):
        """Gère les knobs quand des pads sont maintenus en mode Step Seq."""
        if event.data1 == IDKnob1:
            self.HandleHeldPadsParam(event.data2, pVelocity)
        elif event.data1 == IDKnob2:
            self.HandleHeldPadsParam(event.data2, pPan)
        elif event.data1 == IDKnob3:
            self.HandleHeldPadsParam(event.data2, pModX)
        elif event.data1 == IDKnob4:
            self.HandleHeldPadsParam(event.data2, pModY)

        self.fire.HeldPadsChanged = True
        self.fire.ChangeFlag = True

    def HandleAccentKnobs(self, event):
        """Gère les knobs en mode accent."""
        if event.data1 == IDKnob1:
            self.fire.AccentParams.Vel = utils.Limited(self.fire.AccentParams.Vel + self.fire.AdaptKnobVal(event.outEv), 0, 127)
            self.fire.DisplayBar('Default velocity', self.fire.AccentParams.Vel / 127, False)
        elif event.data1 == IDKnob2:
            self.fire.AccentParams.Pan = utils.Limited(self.fire.AccentParams.Pan + self.fire.AdaptKnobVal(event.outEv), 0, 127)
            self.fire.DisplayBar('Default panning', self.fire.AccentParams.Pan / 127, True)
        elif event.data1 == IDKnob3:
            self.fire.AccentParams.ModX = utils.Limited(self.fire.AccentParams.ModX + self.fire.AdaptKnobVal(event.outEv), 0, 127)
            self.fire.DisplayBar('Default ModX', self.fire.AccentParams.ModX / 127, False)
        elif event.data1 == IDKnob4:
            self.fire.AccentParams.ModY = utils.Limited(self.fire.AccentParams.ModY + self.fire.AdaptKnobVal(event.outEv), 0, 127)
            self.fire.DisplayBar('Default ModY', self.fire.AccentParams.ModY / 127, False)

    # --- Refresh ---

    def Refresh(self, MuteSelOnly=False):
        """Rafraîchit l'affichage des pads en mode Step Sequencer.
        Layout 1x64 : 1 channel sélectionné, 4 rows x 16 cols = 64 steps.
        Row 0 = steps startPos+0..15
        Row 1 = steps startPos+16..31
        Row 2 = steps startPos+32..47
        Row 3 = steps startPos+48..63
        """
        if not device.isAssigned():
            return

        dataOut = bytearray(0)
        index = channels.channelNumber()

        # Mute/Select buttons: all 4 show same channel info
        for row in range(4):
            mute = IDMute1 + row
            slct = IDTrackSel1 + row
            if index >= 0:
                if channels.isChannelMuted(index):
                    self.fire.SendCC(mute, SingleColorOff)
                else:
                    self.fire.SendCC(mute, SingleColorFull)
                if channels.isChannelSelected(index):
                    self.fire.SendCC(slct, SingleColorFull)
                else:
                    self.fire.SendCC(slct, SingleColorOff)
            else:
                self.fire.SendCC(mute, SingleColorOff)
                self.fire.SendCC(slct, SingleColorOff)

        if MuteSelOnly:
            return

        # Get channel color
        if index >= 0:
            c = channels.getChannelColor(index)
            if c == CT_ColorT[CT_Sampler]:
                c = 0xC8C8C8
            h, s, v = utils.RGBToHSVColor(c)
        else:
            h, s, v = 0, 0, 0

        ps = self.fire.GetChanRackStartPos()

        for row in range(4):
            for col in range(16):
                dest = row * 16 + col  # pad index 0..63
                stepPos = ps + row * 16 + col  # absolute step position
                playing = stepPos == self.fire.CurStep
                blinking = False

                if playing:
                    r = 0x0F
                    g = 0x0F
                    b = 0x0F
                    mapVal = 0xFFFFFF
                else:
                    mapVal = 0
                    r = 0
                    g = 0
                    b = 0

                    # Check if this pad is held (blinking)
                    for m in range(0, len(self.fire.HeldPads)):
                        if self.fire.HeldPads[m] == dest:
                            blinking = True
                            if self.fire.BlinkTimer < BlinkSpeed:
                                h2 = h
                                s2 = s
                                v2 = 1
                                c2, h2, s2, v2 = self.fire.ScaleColor(utils.Limited(self.fire.GetStepParam(dest, pVelocity) / 127, 0.1, 1), h2, s2, v2)
                                r2, g2, b2 = utils.HSVtoRGB(h2, s2, v2)
                                r = round((r2 * 255) - RoundAsFloorS) >> 1
                                g = round((g2 * 255) - RoundAsFloorS) >> 1
                                b = round((b2 * 255) - RoundAsFloorS) >> 1
                                mapVal = ((r & 0xFF) << 16) + ((g & 0xFF) << 8) + (b & 0xFF)
                            break

                    if (not blinking) & (index >= 0):
                        if channels.getGridBitWithLoop(index, stepPos) > 0:
                            h2 = h
                            s2 = s
                            v2 = 1
                            res, h2, s2, v2 = self.fire.ScaleColor(utils.Limited(self.fire.GetStepParam(dest, pVelocity) / 127, 0.1, 1), h2, s2, v2)
                            r2, g2, b2 = utils.HSVtoRGB(h2, s2, v2)
                            r = round((r2 * 255) - RoundAsFloorS) >> 1
                            g = round((g2 * 255) - RoundAsFloorS) >> 1
                            b = round((b2 * 255) - RoundAsFloorS) >> 1
                            mapVal = ((r & 0xFF) << 16) + ((g & 0xFF) << 8) + (b & 0xFF)

                if self.fire.BtnMap[dest] != mapVal:
                    dataOut.append(dest)
                    dataOut.append(r)
                    dataOut.append(g)
                    dataOut.append(b)
                    self.fire.BtnMap[dest] = mapVal

        if (len(dataOut) > 0):
            screen.unBlank(True)
            self.fire.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)
