#   name=AKAI FL Studio Fire - Key Sender
#   Ecrit la touche dans un fichier pipe — lu par watcher.py externe

import os
import time

_PIPE_PATH = ''
_PIPE_READY = False
_SEND_SEQ = 0

_SENDKEYS_MAP = {
    'ENTER':     '~',
    'ESCAPE':    '{ESC}',
    'TAB':       '{TAB}',
    'BACKSPACE': '{BS}',
    'DELETE':    '{DEL}',
    'INSERT':    '{INS}',
    'UP':        '{UP}',
    'DOWN':      '{DOWN}',
    'LEFT':      '{LEFT}',
    'RIGHT':     '{RIGHT}',
    'HOME':      '{HOME}',
    'END':       '{END}',
    'PGUP':      '{PGUP}',
    'PGDN':      '{PGDN}',
    'F1':  '{F1}',  'F2':  '{F2}',  'F3':  '{F3}',  'F4':  '{F4}',
    'F5':  '{F5}',  'F6':  '{F6}',  'F7':  '{F7}',  'F8':  '{F8}',
    'F9':  '{F9}',  'F10': '{F10}', 'F11': '{F11}', 'F12': '{F12}',
    'CTRL': '__VK_CTRL__',
    'SHIFT': '__VK_SHIFT__',
    'ALT': '__VK_ALT__',
}

_SENDKEYS_ESCAPE = set('~%^+()[]{}')
_MODIFIER_TOKEN_MAP = {
    'ctrl': {
        'tap': '__VK_CTRL__',
        'down': '__VK_CTRL_DOWN__',
        'up': '__VK_CTRL_UP__',
    },
    'shift': {
        'tap': '__VK_SHIFT__',
        'down': '__VK_SHIFT_DOWN__',
        'up': '__VK_SHIFT_UP__',
    },
    'alt': {
        'tap': '__VK_ALT__',
        'down': '__VK_ALT_DOWN__',
        'up': '__VK_ALT_UP__',
    },
}


def _EnsurePipe():
    global _PIPE_PATH, _PIPE_READY
    if _PIPE_READY:
        return True
    try:
        _PIPE_PATH = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '_sendkey_pipe.txt'
        )
        print('KeySender pipe: ' + _PIPE_PATH)
        _PIPE_READY = True
        return True
    except Exception as e:
        print('KeySender pipe setup error: ' + str(e))
        return False


def _GetSingleModifierName(ctrl=False, shift=False, alt=False):
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


def _BuildSendKeysString(key, ctrl=False, shift=False, alt=False, action='tap'):
    if key == '':
        modifier = _GetSingleModifierName(ctrl=ctrl, shift=shift, alt=alt)
        if modifier:
            action_name = action if action in ('tap', 'down', 'up') else 'tap'
            return _MODIFIER_TOKEN_MAP[modifier][action_name]
        return ''

    sk = ''
    if ctrl:  sk += '^'
    if alt:   sk += '%'
    if shift: sk += '+'
    upper = key.upper()
    if upper in _SENDKEYS_MAP:
        sk += _SENDKEYS_MAP[upper]
    elif len(key) == 1 and key in _SENDKEYS_ESCAPE:
        sk += '{' + key + '}'
    else:
        sk += key.lower()
    return sk


def SendKey(key, ctrl=False, shift=False, alt=False, action='tap'):
    """Ecrit la touche dans le fichier pipe — watcher.py l'envoie a FL."""
    global _SEND_SEQ
    if not _EnsurePipe():
        return False
    try:
        sk = _BuildSendKeysString(key, ctrl, shift, alt, action=action)
        if sk == '':
            return False
        _SEND_SEQ += 1
        payload = '__SEQ__' + str(_SEND_SEQ) + '|' + sk
        with open(_PIPE_PATH, 'w') as f:
            f.write(payload + '\n')
        print('KeySender pipe write: ' + payload)
        return True
    except Exception as e:
        print('KeySender error: ' + str(e))
        return False
