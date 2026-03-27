#   name=AKAI FL Studio Fire - FL Control Mode
#   Row0=Mixer ou ChannelRack (Mute1/Mute2 toggle), Row1=Pattern select,
#   Row2=Playlist tools (Mute3 swap page A/B), Row3=Piano Roll tools (Mute4 swap page A/B)
#   Pads 11-13 sur rows 2-3 = SendKey fixes, pads 14-16 = navigation API
#   Undo/Redo restent sur Grid L/R (device_Fire.py)

import mixer
import patterns
import channels
import transport
import ui
import device
import general
import screen
import utils
import time

from fire_modules.mode_base import FireModeBase
from fire_modules.constants import *

try:
    from fire_modules.key_sender import SendKey
except ImportError:
    print("FLControl: SendKey non disponible")
    SendKey = None

try:
    from fire_modules.fl_control_config import (
        FIXED_SENDKEYS as _CONFIG_FIXED_SENDKEYS,
        ROW2_SHORTCUTS_A as _CONFIG_ROW2_SHORTCUTS_A,
        ROW2_SHORTCUTS_B as _CONFIG_ROW2_SHORTCUTS_B,
        ROW3_SHORTCUTS_A as _CONFIG_ROW3_SHORTCUTS_A,
        ROW3_SHORTCUTS_B as _CONFIG_ROW3_SHORTCUTS_B,
        SWAPPABLE_PAD_COUNT as _CONFIG_SWAPPABLE_PAD_COUNT,
    )
except Exception as exc:
    print("FLControl: config fallback: " + str(exc))
    _CONFIG_SWAPPABLE_PAD_COUNT = 10
    _CONFIG_ROW2_SHORTCUTS_A = [
        ('p', False, False, False, 'Draw',     0xFF6600),
        ('b', False, False, False, 'Paint',    0x00CCCC),
        ('d', False, False, False, 'Delete',   0xFF0000),
        ('t', False, False, False, 'Mute',     0xFF4488),
        ('s', False, False, False, 'Slip',     0xFF8800),
        ('c', False, False, False, 'Slice',    0x0066FF),
        ('e', False, False, False, 'Select',   0xFFFF00),
        ('z', False, False, False, 'Zoom',     0xAA00FF),
        ('y', False, False, False, 'Playback', 0xFF4488),
        ('',  False, False, False, 'PL-A10',   0x220022),
    ]
    _CONFIG_ROW2_SHORTCUTS_B = [
        ('', False, False, False, 'PL-B1', 0x442200),
        ('', False, False, False, 'PL-B2', 0x442200),
        ('', False, False, False, 'PL-B3', 0x442200),
        ('', False, False, False, 'PL-B4', 0x442200),
        ('', False, False, False, 'PL-B5', 0x442200),
        ('', False, False, False, 'PL-B6', 0x442200),
        ('', False, False, False, 'PL-B7', 0x442200),
        ('', False, False, False, 'PL-B8', 0x442200),
        ('', False, False, False, 'PL-B9', 0x442200),
        ('', False, False, False, 'PL-B10', 0x442200),
    ]
    _CONFIG_ROW3_SHORTCUTS_A = [
        ('p', False, False, False, 'Draw',     0xFF6600),
        ('b', False, False, False, 'Paint',    0x00CCCC),
        ('d', False, False, False, 'Delete',   0xFF0000),
        ('t', False, False, False, 'Mute',     0xFF4488),
        ('n', False, False, False, 'PaintD',   0xAA00FF),
        ('c', False, False, False, 'Slice',    0x0066FF),
        ('e', False, False, False, 'Select',   0xFFFF00),
        ('z', False, False, False, 'Zoom',     0xAA00FF),
        ('y', False, False, False, 'Playback', 0xFF4488),
        ('',  False, False, False, 'PR-A10',   0x220022),
    ]
    _CONFIG_ROW3_SHORTCUTS_B = [
        ('', False, False, False, 'PR-B1', 0x442200),
        ('', False, False, False, 'PR-B2', 0x442200),
        ('', False, False, False, 'PR-B3', 0x442200),
        ('', False, False, False, 'PR-B4', 0x442200),
        ('', False, False, False, 'PR-B5', 0x442200),
        ('', False, False, False, 'PR-B6', 0x442200),
        ('', False, False, False, 'PR-B7', 0x442200),
        ('', False, False, False, 'PR-B8', 0x442200),
        ('', False, False, False, 'PR-B9', 0x442200),
        ('', False, False, False, 'PR-B10', 0x442200),
    ]
    _CONFIG_FIXED_SENDKEYS = {
        'row2_11': ('', False, False, False, '', 0x000000),
        'row2_12': ('', False, False, False, '', 0x000000),
        'row2_13': ('', False, False, False, '', 0x000000),
        'row3_11': ('', False, False, False, '', 0x000000),
        'row3_12': ('', False, False, False, '', 0x000000),
        'row3_13': ('', False, False, False, '', 0x000000),
    }

from midi import *

# ============================
# Pad Layout
# ============================
# Row 0 (top): 16 Mixer tracks OU 16 Channel Rack (toggle via Mute1/Mute2)
# Row 1: 16 pattern select (patterns 1-16)
# Row 2: Playlist tools page A/B (Mute3 toggle), pads 11-13 SendKey, 14-16 API
# Row 3: Piano Roll tools page A/B (Mute4 toggle), pads 11-13 SendKey, 14-16 API

# Pad function IDs
FLC_NONE = 0
FLC_MIXER_MUTE = 1
FLC_PATTERN_SEL = 2
FLC_PL_TOOL = 3
FLC_PR_TOOL = 4
FLC_ARROW = 5
FLC_SHORTCUT = 6
FLC_USER = 7
FLC_CHAN_RACK = 8
FLC_FIXED_SENDKEY = 9

# Row 0 source modes
ROW0_MIXER = 0
ROW0_CHAN = 1

def _NormalizeShortcut(entry, fallback_label, fallback_color):
    if not isinstance(entry, (list, tuple)):
        return ('', False, False, False, fallback_label, fallback_color)

    key = ''
    ctrl = False
    shift = False
    alt = False
    label = fallback_label
    color = fallback_color

    if len(entry) > 0 and entry[0] is not None:
        key = str(entry[0])
    if len(entry) > 1:
        ctrl = bool(entry[1])
    if len(entry) > 2:
        shift = bool(entry[2])
    if len(entry) > 3:
        alt = bool(entry[3])
    if len(entry) > 4 and entry[4] is not None and str(entry[4]) != '':
        label = str(entry[4])
    if len(entry) > 5:
        try:
            color = int(entry[5]) & 0xFFFFFF
        except Exception:
            color = fallback_color

    return (key, ctrl, shift, alt, label, color)


def _NormalizeShortcutList(entries, count, prefix, fallback_color):
    result = []
    source = entries if isinstance(entries, list) else []
    for idx in range(count):
        fallback_label = prefix + str(idx + 1)
        entry = source[idx] if idx < len(source) else None
        result.append(_NormalizeShortcut(entry, fallback_label, fallback_color))
    return result


def _NormalizeFixedSendKeys(entries):
    source = entries if isinstance(entries, dict) else {}
    names = (
        'row2_11', 'row2_12', 'row2_13',
        'row3_11', 'row3_12', 'row3_13',
    )
    result = {}
    for name in names:
        result[name] = _NormalizeShortcut(source.get(name), '', 0x000000)
    return result

# Colors (0xRRGGBB)
COL_MIXER_ON = 0x00FF00       # green = track unmuted (active)
COL_MIXER_OFF = 0x003300      # dim green = track muted
COL_MIXER_SEL = 0x00FF88      # bright green-cyan = selected mixer track
COL_CHAN_ON = 0xFF8800        # orange vif = channel unmuted
COL_CHAN_OFF = 0x331100        # dim orange = channel muted
COL_CHAN_SEL = 0xFFCC00       # bright yellow-orange = selected channel
COL_PAT_ACTIVE = 0x0066FF     # blue = current pattern
COL_PAT_EXIST = 0x001844      # dim blue = pattern exists
COL_PAT_EMPTY = 0x000811      # very dim = no pattern data
COL_ARROW = 0xFF0000          # red for arrow keys
COL_ENTER = 0x00FF00          # green for enter
COL_ESCAPE = 0x0000FF         # blue for escape
COL_USER = 0x220022           # very dim purple = unassigned user
COL_OFF = 0x000000
COL_PLACEHOLDER = 0x442200    # dim amber = placeholder for future shortcuts

RECT_TIME = 5000              # durée rectangle rouge FL Studio (ms)

SWAPPABLE_PAD_COUNT = max(0, min(10, int(_CONFIG_SWAPPABLE_PAD_COUNT)))
ROW2_SHORTCUTS_A = _NormalizeShortcutList(_CONFIG_ROW2_SHORTCUTS_A, SWAPPABLE_PAD_COUNT, 'PL-A', COL_USER)
ROW2_SHORTCUTS_B = _NormalizeShortcutList(_CONFIG_ROW2_SHORTCUTS_B, SWAPPABLE_PAD_COUNT, 'PL-B', COL_PLACEHOLDER)
ROW3_SHORTCUTS_A = _NormalizeShortcutList(_CONFIG_ROW3_SHORTCUTS_A, SWAPPABLE_PAD_COUNT, 'PR-A', COL_USER)
ROW3_SHORTCUTS_B = _NormalizeShortcutList(_CONFIG_ROW3_SHORTCUTS_B, SWAPPABLE_PAD_COUNT, 'PR-B', COL_PLACEHOLDER)
FIXED_SENDKEYS = _NormalizeFixedSendKeys(_CONFIG_FIXED_SENDKEYS)


class FLControlMode(FireModeBase):
    """Mode FL Control : Mixer/ChannelRack, Patterns, outils Playlist/Piano Roll."""

    def __init__(self, fire_device):
        super().__init__(fire_device)
        self._row0Mode = ROW0_MIXER   # ROW0_MIXER ou ROW0_CHAN
        self._row0Page = 0            # 0 = pistes 1-16, 1 = pistes 17-32
        self._row2Page = 0            # 0 = page A, 1 = page B
        self._row3Page = 0            # 0 = page A, 1 = page B

    # ==========================
    # Tool list helpers
    # ==========================

    def _GetPLTools(self):
        """Return current Playlist tools list (page A or B)."""
        return ROW2_SHORTCUTS_B if self._row2Page else ROW2_SHORTCUTS_A

    def _GetPRTools(self):
        """Return current Piano Roll tools list (page A or B)."""
        return ROW3_SHORTCUTS_B if self._row3Page else ROW3_SHORTCUTS_A

    def _GetFixedSendKey(self, idx):
        """Return configured fixed SendKey entry for row 2 or row 3."""
        row = idx // 10
        pad_num = 11 + (idx % 10)
        return FIXED_SENDKEYS.get('row' + str(row) + '_' + str(pad_num), ('', False, False, False, '', COL_OFF))

    def _GetModifierOnlyName(self, shortcut):
        """Return ctrl/shift/alt when shortcut is a bare modifier, else empty."""
        key, ctrl, shift, alt, _, _ = shortcut
        if key:
            return ''

        enabled = []
        if ctrl:
            enabled.append('ctrl')
        if shift:
            enabled.append('shift')
        if alt:
            enabled.append('alt')

        if len(enabled) == 1:
            return enabled[0]
        return ''

    # ==========================
    # Pad mapping
    # ==========================

    def _GetPadInfo(self, pad_num):
        """Return (function_type, index) for a given pad number."""
        row = pad_num // PadsStride
        col = pad_num % PadsStride
        if col >= 16:
            return (FLC_NONE, 0)

        if row == 0:
            # Row 0: Mixer or Channel Rack (depending on _row0Mode)
            if self._row0Mode == ROW0_MIXER:
                return (FLC_MIXER_MUTE, col)
            else:
                return (FLC_CHAN_RACK, col)
        elif row == 1:
            # Row 1: 16 pattern select
            return (FLC_PATTERN_SEL, col)
        elif row == 2:
            # Row 2: PL tools (0-9 swappable), SendKey fixes (10-12), API nav (13-15)
            if col < SWAPPABLE_PAD_COUNT:
                return (FLC_PL_TOOL, col)
            elif col <= 12:
                return (FLC_FIXED_SENDKEY, 20 + (col - 10))
            elif col == 13:
                return (FLC_SHORTCUT, 101)  # Escape
            elif col == 14:
                return (FLC_ARROW, 0)  # Up
            elif col == 15:
                return (FLC_SHORTCUT, 100)  # Enter
        elif row == 3:
            # Row 3: PR tools (0-9 swappable), SendKey fixes (10-12), API nav (13-15)
            if col < SWAPPABLE_PAD_COUNT:
                return (FLC_PR_TOOL, col)
            elif col <= 12:
                return (FLC_FIXED_SENDKEY, 30 + (col - 10))
            elif col == 13:
                return (FLC_ARROW, 2)  # Left
            elif col == 14:
                return (FLC_ARROW, 1)  # Down
            elif col == 15:
                return (FLC_ARROW, 3)  # Right

        return (FLC_NONE, 0)

    # ==========================
    # Focus helpers
    # ==========================

    def _FocusPlaylist(self):
        """Ensure Playlist is visible and focused."""
        try:
            if not ui.getVisible(widPlaylist):
                ui.showWindow(widPlaylist)
            ui.setFocused(widPlaylist)
        except Exception:
            pass

    def _FocusPianoRoll(self):
        """Ensure Piano Roll is visible and focused."""
        try:
            if not ui.getVisible(widPianoRoll):
                ui.showWindow(widPianoRoll)
            ui.setFocused(widPianoRoll)
        except Exception:
            pass

    # ==========================
    # Pad Event
    # ==========================

    def OnPadEvent(self, event, pad_num):
        """Handle pad press in FL Control mode."""
        func, idx = self._GetPadInfo(pad_num)
        is_release = (event.data2 == 0) or ((getattr(event, 'status', 0) & 0xF0) == MIDI_NOTEOFF)

        if func == FLC_MIXER_MUTE:
            if is_release:
                event.handled = True
                return
            self._HandleMixerMute(idx)
        elif func == FLC_CHAN_RACK:
            if is_release:
                event.handled = True
                return
            self._HandleChanRack(idx)
        elif func == FLC_PATTERN_SEL:
            if is_release:
                event.handled = True
                return
            self._HandlePatternSelect(idx)
        elif func == FLC_PL_TOOL:
            self._HandlePlaylistTool(idx, not is_release)
        elif func == FLC_PR_TOOL:
            self._HandlePianoRollTool(idx, not is_release)
        elif func == FLC_FIXED_SENDKEY:
            self._HandleFixedSendKey(idx, not is_release)
        elif func == FLC_ARROW:
            if is_release:
                event.handled = True
                return
            self._HandleArrow(idx)
        elif func == FLC_SHORTCUT:
            if is_release:
                event.handled = True
                return
            self._HandleShortcut(idx)
        elif func == FLC_USER:
            pass  # Pads éteints / placeholders

        event.handled = True

    # ==========================
    # Action handlers
    # ==========================

    def _HandleMixerMute(self, col):
        """Select mixer track, or Shift+pad to mute."""
        track = self._row0Page * 16 + col + 1
        if track >= mixer.trackCount():
            return
        if self.fire.ShiftHeld:
            mixer.muteTrack(track)
            name = mixer.getTrackName(track)
            muted = mixer.isTrackMuted(track)
            self.fire.DisplayTimedText('Mixer ' + str(track) + ': ' + name + chr(13) + ('MUTED' if muted else 'ACTIVE'))
        else:
            mixer.setTrackNumber(track, curfxScrollToMakeVisible)
            ui.miDisplayRect(track, track, RECT_TIME, CR_ScrollToView)
            self.fire.DisplayTimedText('Mixer ' + str(track) + ': ' + mixer.getTrackName(track))
        self.Refresh()

    def _HandleChanRack(self, col):
        """Select channel, double-click to open Channel Editor, Shift+pad to mute."""
        idx = self._row0Page * 16 + col
        if idx >= channels.channelCount():
            return
        if self.fire.ShiftHeld:
            channels.muteChannel(idx)
            name = channels.getChannelName(idx)
            muted = channels.isChannelMuted(idx)
            self.fire.DisplayTimedText('Chan ' + str(idx) + ': ' + name + chr(13) + ('MUTED' if muted else 'ACTIVE'))
        else:
            prevChan = channels.channelNumber()
            channels.selectOneChannel(idx)
            ui.crDisplayRect(0, idx, 0, 1, RECT_TIME, CR_ScrollToView + CR_HighlightChannels)
            if idx == prevChan:
                # Double-click: ouvre/focus l'éditeur du channel (comme NFX v2)
                self._OpenChannelEditor(idx)
            else:
                self.fire.DisplayTimedText('Chan ' + str(idx) + ': ' + channels.getChannelName(idx))
        self.Refresh()

    def _OpenChannelEditor(self, idx):
        """Open channel editor based on channel type (NFX v2 logic)."""
        try:
            channelType = channels.getChannelType(idx)
            # Toggle: si déjà focus sur plugin, ferme, sinon ouvre
            isFocused = ui.getFocused(widPlugin) or ui.getFocused(widPluginGenerator)
            showVal = 0 if isFocused else 1
            
            # Types de channels qui utilisent showEditor (plugins)
            if channelType in [CT_Hybrid, CT_GenPlug]:
                channels.showEditor(idx, showVal)
                self.fire.DisplayTimedText('Channel Editor')
            # Types de channels qui utilisent showCSForm (sampler, layer, audio)
            elif channelType in [CT_Layer, CT_AudioClip, CT_Sampler, CT_AutoClip]:
                channels.showCSForm(idx, showVal)
                self.fire.DisplayTimedText('Channel Settings')
            else:
                # Fallback: ouvre le Channel Rack
                if not ui.getVisible(widChannelRack):
                    ui.showWindow(widChannelRack)
                ui.setFocused(widChannelRack)
                self.fire.DisplayTimedText('Channel Rack')
                
            # Si on ferme, revenir au Channel Rack
            if showVal == 0:
                ui.showWindow(widChannelRack)
        except Exception as e:
            print('FLControl OpenChannelEditor error:', str(e))
            # Fallback simple
            if not ui.getVisible(widChannelRack):
                ui.showWindow(widChannelRack)
            ui.setFocused(widChannelRack)

    def _HandlePatternSelect(self, col):
        """Select pattern (col 0-15 -> pattern 1-16)."""
        pat = col + 1
        if pat <= patterns.patternMax() + 1:
            patterns.jumpToPattern(pat)
            self.fire.DisplayTimedText('Pattern ' + str(pat))
        self.Refresh()

    def _SendConfiguredShortcut(self, shortcut, prefix, is_press):
        """Send configured shortcut, with hold support for bare modifiers only."""
        key, ctrl, shift, alt, label, _ = shortcut
        if SendKey is None:
            return

        modifier = self._GetModifierOnlyName(shortcut)
        if modifier:
            SendKey(
                '',
                ctrl=(modifier == 'ctrl'),
                shift=(modifier == 'shift'),
                alt=(modifier == 'alt'),
                action='down' if is_press else 'up'
            )
            if is_press:
                self.fire.DisplayTimedText(prefix + (label if label else modifier.upper()))
            return

        if not is_press:
            return

        if not key and not (ctrl or shift or alt):
            return

        SendKey(key, ctrl=ctrl, shift=shift, alt=alt)
        self.fire.DisplayTimedText(prefix + (label if label else key))

    def _HandlePlaylistTool(self, idx, is_press=True):
        """Handle configured Playlist shortcut."""
        tools = self._GetPLTools()
        if idx >= len(tools):
            return
        self._SendConfiguredShortcut(tools[idx], 'Playlist: ', is_press)

    def _HandlePianoRollTool(self, idx, is_press=True):
        """Handle configured Piano Roll shortcut."""
        tools = self._GetPRTools()
        if idx >= len(tools):
            return
        self._SendConfiguredShortcut(tools[idx], 'PianoRoll: ', is_press)

    def _HandleFixedSendKey(self, idx, is_press=True):
        """Handle row-specific fixed SendKey pads."""
        shortcut = self._GetFixedSendKey(idx)
        if idx // 10 == 2:
            self._SendConfiguredShortcut(shortcut, 'Playlist: ', is_press)
        else:
            self._SendConfiguredShortcut(shortcut, 'PianoRoll: ', is_press)

    def _HandleArrow(self, direction):
        """Send arrow key. 0=Up, 1=Down, 2=Left, 3=Right."""
        if direction == 0:
            transport.globalTransport(FPT_Up, 1)
        elif direction == 1:
            transport.globalTransport(FPT_Down, 1)
        elif direction == 2:
            transport.globalTransport(FPT_Left, 1)
        elif direction == 3:
            transport.globalTransport(FPT_Right, 1)

    def _HandleShortcut(self, idx):
        """Handle Enter/Escape shortcut pads."""
        if idx == 100:
            transport.globalTransport(FPT_Enter, 1)
        elif idx == 101:
            transport.globalTransport(FPT_Escape, 1)

    # ==========================
    # Mute button handlers (Row0 mode + shortcut pages)
    # ==========================

    def HandleMuteButton(self, btn_index):
        """Mute1=Mixer toggle page, Mute2=ChanRack toggle page,
           Mute3=Row2 swap page A/B, Mute4=Row3 swap page A/B."""
        if btn_index == 0:
            # Mute 1: Mixer mode
            if self._row0Mode == ROW0_MIXER:
                # Déjà en Mixer: toggle page 1/2
                self._row0Page = 1 - self._row0Page
                start = self._row0Page * 16 + 1
                txt = 'Mixer ' + str(start) + '-' + str(start + 15)
            else:
                # Switch vers Mixer, page 0
                self._row0Mode = ROW0_MIXER
                self._row0Page = 0
                txt = 'Mixer 1-16'
            self.fire.ClearBtnMap()
            self.Refresh()
            self._UpdateMuteLEDs()
            return txt

        elif btn_index == 1:
            # Mute 2: Channel Rack mode
            if self._row0Mode == ROW0_CHAN:
                # Déjà en Chan: toggle page 1/2
                self._row0Page = 1 - self._row0Page
                start = self._row0Page * 16
                txt = 'ChanRack ' + str(start) + '-' + str(start + 15)
            else:
                # Switch vers Channel Rack, page 0
                self._row0Mode = ROW0_CHAN
                self._row0Page = 0
                txt = 'ChanRack 0-15'
            self.fire.ClearBtnMap()
            self.Refresh()
            self._UpdateMuteLEDs()
            return txt

        elif btn_index == 2:
            # Mute 3: Toggle Row 2 shortcut page A/B
            self._row2Page = 1 - self._row2Page
            page = 'B' if self._row2Page else 'A'
            self.fire.ClearBtnMap()
            self.Refresh()
            self._UpdateMuteLEDs()
            return 'PL Tools: Page ' + page

        elif btn_index == 3:
            # Mute 4: Toggle Row 3 shortcut page A/B
            self._row3Page = 1 - self._row3Page
            page = 'B' if self._row3Page else 'A'
            self.fire.ClearBtnMap()
            self.Refresh()
            self._UpdateMuteLEDs()
            return 'PR Tools: Page ' + page

        return ''

    def _UpdateMuteLEDs(self):
        """Update Mute button LEDs to reflect current state."""
        # Mute buttons: jaune si actif page 0, éteint si page 1 (LED strip TrackSel indique page 2)
        if self._row0Mode == ROW0_MIXER:
            self.fire.SendCC(IDMute1, SingleColorFull if self._row0Page == 0 else SingleColorOff)
        else:
            self.fire.SendCC(IDMute1, SingleColorOff)
        # Mute2: jaune si Chan actif page 0, éteint si page 1
        if self._row0Mode == ROW0_CHAN:
            self.fire.SendCC(IDMute2, SingleColorFull if self._row0Page == 0 else SingleColorOff)
        else:
            self.fire.SendCC(IDMute2, SingleColorOff)
        # Mute3: jaune si page A, éteint si page B
        self.fire.SendCC(IDMute3, SingleColorFull if self._row2Page == 0 else SingleColorOff)
        # Mute4: jaune si page A, éteint si page B
        self.fire.SendCC(IDMute4, SingleColorFull if self._row3Page == 0 else SingleColorOff)
        
        # TrackSel LEDs: indiquent les pages 2 (17-32) ou pages B
        self._UpdateTrackSelLEDs()

    def _UpdateTrackSelLEDs(self):
        """Update TrackSel LEDs to indicate page 2/B states."""
        # Éteindre tout d'abord
        for i in range(4):
            self.fire.SendCC(IDTrackSel1 + i, SingleColorOff)
        
        # TrackSel1 = Mixer page 2
        if self._row0Mode == ROW0_MIXER and self._row0Page == 1:
            self.fire.SendCC(IDTrackSel1, SingleColorFull)
        # TrackSel2 = Channel Rack page 2
        elif self._row0Mode == ROW0_CHAN and self._row0Page == 1:
            self.fire.SendCC(IDTrackSel2, SingleColorFull)
        # TrackSel3 = Row 2 page B
        if self._row2Page == 1:
            self.fire.SendCC(IDTrackSel3, SingleColorFull)
        # TrackSel4 = Row 3 page B
        if self._row3Page == 1:
            self.fire.SendCC(IDTrackSel4, SingleColorFull)

    # ==========================
    # Touch knob handlers
    # ==========================

    def HandleKnobTouch(self, knob_id):
        """Touch knobs open/close FL windows."""
        if knob_id == IDKnob1:
            transport.globalTransport(FPT_F6, 1)
            return 'Channel Rack'
        elif knob_id == IDKnob2:
            transport.globalTransport(FPT_F7, 1)
            return 'Piano Roll'
        elif knob_id == IDKnob3:
            transport.globalTransport(FPT_F9, 1)
            return 'Mixer'
        elif knob_id == IDKnob4:
            transport.globalTransport(FPT_F5, 1)
            return 'Playlist'
        return ''

    # ==========================
    # Refresh
    # ==========================

    def _GetPadColor(self, pad_num):
        """Get color for a pad based on function and state."""
        func, idx = self._GetPadInfo(pad_num)

        if func == FLC_MIXER_MUTE:
            track = self._row0Page * 16 + idx + 1
            if track >= mixer.trackCount():
                return COL_OFF
            if track == mixer.trackNumber():
                return COL_MIXER_SEL
            if mixer.isTrackMuted(track):
                return COL_MIXER_OFF
            return COL_MIXER_ON

        elif func == FLC_CHAN_RACK:
            ch = self._row0Page * 16 + idx
            if ch >= channels.channelCount():
                return COL_OFF
            if ch == channels.channelNumber():
                return COL_CHAN_SEL
            if channels.isChannelMuted(ch):
                return COL_CHAN_OFF
            return COL_CHAN_ON

        elif func == FLC_PATTERN_SEL:
            pat = idx + 1
            curPat = patterns.patternNumber()
            if pat == curPat:
                return COL_PAT_ACTIVE
            elif pat <= patterns.patternCount():
                return COL_PAT_EXIST
            else:
                return COL_PAT_EMPTY

        elif func == FLC_PL_TOOL:
            tools = self._GetPLTools()
            if idx < len(tools):
                return tools[idx][5]
            return COL_OFF

        elif func == FLC_PR_TOOL:
            tools = self._GetPRTools()
            if idx < len(tools):
                return tools[idx][5]
            return COL_OFF

        elif func == FLC_FIXED_SENDKEY:
            return self._GetFixedSendKey(idx)[5]

        elif func == FLC_ARROW:
            return COL_ARROW

        elif func == FLC_SHORTCUT:
            if idx == 100:
                return COL_ENTER
            elif idx == 101:
                return COL_ESCAPE
            return COL_USER

        elif func == FLC_USER:
            return COL_USER

        return COL_OFF

    def Refresh(self):
        """Refresh all 64 pads."""
        if not device.isAssigned():
            return

        dataOut = bytearray(0)

        for row in range(4):
            for col in range(16):
                pad_num = row * PadsStride + col
                color = self._GetPadColor(pad_num)

                if self.fire.BtnMap[pad_num] != color:
                    r = ((color >> 16) & 0xFF) >> 1
                    g = ((color >> 8) & 0xFF) >> 1
                    b = (color & 0xFF) >> 1
                    dataOut.append(pad_num)
                    dataOut.append(r & 0x7F)
                    dataOut.append(g & 0x7F)
                    dataOut.append(b & 0x7F)
                    self.fire.BtnMap[pad_num] = color

        if len(dataOut) > 0:
            screen.unBlank(True)
            self.fire.SendMessageToDevice(MsgIDSetRGBPadLedState, len(dataOut), dataOut)

    def OnActivate(self):
        """Called when FL Control mode becomes active."""
        self.fire.ClearBtnMap()
        self.Refresh()
        self._UpdateMuteLEDs()

    def OnDeactivate(self):
        """Called when leaving FL Control mode."""
        # Éteindre les LEDs Mute
        self.fire.SendCC(IDMute1, SingleColorOff)
        self.fire.SendCC(IDMute2, SingleColorOff)
        self.fire.SendCC(IDMute3, SingleColorOff)
        self.fire.SendCC(IDMute4, SingleColorOff)
        # Éteindre les LEDs TrackSel
        for i in range(4):
            self.fire.SendCC(IDTrackSel1 + i, SingleColorOff)
