#   name=AKAI FL Studio Fire - FL Control Config
#   Central file for FL Control shortcuts

SWAPPABLE_PAD_COUNT = 9
FIXED_SENDKEY_PAD_NUMBERS = (10, 11, 12, 13)

# Format:
# (key, ctrl, shift, alt, label, color)

# ==========================================
# PLAYLIST - ROW 3 - PAGE A (pads 1-9)
# ==========================================
ROW2_SHORTCUTS_A = [
    ('p', False, False, False, 'Draw', 0xFF6600),
    ('b', False, False, False, 'Paint', 0x00CCCC),
    ('d', False, False, False, 'Delete', 0xFF0000),
    ('t', False, False, False, 'Mute', 0xFF4488),
    ('s', False, False, False, 'Slip', 0xFF8800),
    ('c', False, False, False, 'Slice', 0x0066FF),
    ('e', False, False, False, 'Select', 0xFFFF00),
    ('z', False, False, False, 'Zoom', 0xAA00FF),
    ('y', False, False, False, 'Playback', 0xFF4488),
]

# ==========================================
# PLAYLIST - ROW 3 - PAGE B (pads 1-9)
# ==========================================
ROW2_SHORTCUTS_B = [
    ('', False, False, False, 'PL-B1', 0x442200),
    ('', False, False, False, 'PL-B2', 0x442200),
    ('', False, False, False, 'PL-B3', 0x442200),
    ('', False, False, False, 'PL-B4', 0x442200),
    ('', False, False, False, 'PL-B5', 0x442200),
    ('', False, False, False, 'PL-B6', 0x442200),
    ('', False, False, False, 'PL-B7', 0x442200),
    ('', False, False, False, 'PL-B8', 0x442200),
    ('', False, False, False, 'PL-B9', 0x442200),
]

# ==========================================
# PIANO ROLL - ROW 4 - PAGE A (pads 1-9)
# ==========================================
ROW3_SHORTCUTS_A = [
    ('p', False, False, False, 'Draw', 0xFF6600),
    ('b', False, False, False, 'Paint', 0x00CCCC),
    ('d', False, False, False, 'Delete', 0xFF0000),
    ('t', False, False, False, 'Mute', 0xFF4488),
    ('n', False, False, False, 'PaintD', 0xAA00FF),
    ('c', False, False, False, 'Slice', 0x0066FF),
    ('e', False, False, False, 'Select', 0xFFFF00),
    ('z', False, False, False, 'Zoom', 0xAA00FF),
    ('y', False, False, False, 'Playback', 0xFF4488),
]

# ==========================================
# PIANO ROLL - ROW 4 - PAGE B (pads 1-9)
# ==========================================
ROW3_SHORTCUTS_B = [
    ('', False, False, False, 'PR-B1', 0x442200),
    ('', False, False, False, 'PR-B2', 0x442200),
    ('', False, False, False, 'PR-B3', 0x442200),
    ('', False, False, False, 'PR-B4', 0x442200),
    ('', False, False, False, 'PR-B5', 0x442200),
    ('', False, False, False, 'PR-B6', 0x442200),
    ('', False, False, False, 'PR-B7', 0x442200),
    ('', False, False, False, 'PR-B8', 0x442200),
    ('', False, False, False, 'PR-B9', 0x442200),
]

# ==========================================
# FIXED SENDKEYS - ROW 3 / ROW 4 (pads 10-13)
# ==========================================
FIXED_SENDKEYS = {
    'row3_10': ('', False, False, False, '', 0x000000),
    'row3_11': ('', False, False, False, '', 0x000000),
    'row3_12': ('', False, False, False, '', 0x000000),
    'row3_13': ('', False, False, False, '', 0x000000),
    'row4_10': ('', False, False, False, '', 0x000000),
    'row4_11': ('', False, False, False, '', 0x000000),
    'row4_12': ('', False, False, False, '', 0x000000),
    'row4_13': ('', False, False, False, '', 0x000000),
}

# Pads API fixes, gardes dans le code principal:
# Row 3: pad 14 = Escape, pad 15 = Up, pad 16 = Enter
# Row 4: pad 14 = Left,   pad 15 = Down, pad 16 = Right
