# Akai Fire EndGAme V1.1

![FL Studio](https://img.shields.io/badge/FL%20Studio-Hardware%20Script-orange)
![Akai Fire](https://img.shields.io/badge/Akai-Fire-cc5500)
![Platform](https://img.shields.io/badge/Platform-Windows-blue)
![Language](https://img.shields.io/badge/Language-Python-3776ab)
![Docs](https://img.shields.io/badge/Docs-FR%20%2F%20EN-2f855a)

A full custom Akai Fire script for FL Studio focused on workflow speed, vertical sequencing, live performance control, and deep FL Studio shortcut integration.
Goodbye keyboard, everything's on fire !!

This project rethinks the Fire around 4 main modes:

- `STEP`: classic `1x64` sequencing plus vertical `MONO`, `POLY`, and `POLY CHORD` modes
- `NOTE`: chromatic keyboard with optional automatic chord playback
- `CTRL FL`: direct FL Studio control for mixer, channel rack, playlist, piano roll, and custom shortcuts
- `PERFORM`: live sync mode for mutes, relaunches, and pattern switching

## Documentation

- [English PDF guide](./Doc%201%20EndGAme%20ENG.pdf)
- [French PDF guide](./Doc%201%20EndGAme%20FR.pdf)

## Why this project

The stock Akai Fire workflow is useful, but limited.

Akai Fire EndGAme pushes the controller much further with:

- a vertical piano-roll-inspired sequencer
- chord-aware note entry
- direct FL Studio shortcut triggering from the pad matrix
- a dedicated live performance system outside FL Studio's native performance mode
- multi-device STEP expansion for larger visible sequencing areas

## Included files

- [`device_Fire.py`](./device_Fire.py): main FL Studio device script
- [`fire_modules/`](./fire_modules): modular handlers for each mode
- [`fl_control_editor.py`](./fl_control_editor.py): shortcut editor source
- `FLControlEditor.exe`: shortcut editor build
- `fire_modules/AkaiFireWatcher.exe`: companion watcher tool used by the project

## Quick start

1. Copy the `Akai Fire EndGAme` folder into your FL Studio hardware scripts folder.
2. Launch `AkaiFireWatcher.exe`.
3. Power on the Akai Fire.
4. Launch FL Studio.
5. In MIDI settings, select the script and use the same port for input and output.

For full setup and usage details, use the documentation links above.

## Highlights

- `STEP 1`: classic `1x64` step sequencing
- `STEP 2`: vertical mono note sequencing
- `STEP 3`: vertical poly sequencing
- `STEP 4`: vertical poly sequencing with automatic chords
- `NOTE`: playable 4-octave chromatic layout
- `CTRL FL`: playlist and piano roll tools directly on the pads
- `PERFORM`: synchronized mute and pattern switching logic

## Important note

Vertical STEP modes are limited by the FL Studio API.

The Fire can play and display chords internally, but FL Studio may only show the lowest note of a step in its native piano roll or channel rack representation.

To work around this, the project includes sequence export/import support.

## Repository structure

```text
.
|-- device_Fire.py
|-- fl_control_editor.py
|-- FLControlEditor.exe
|-- Doc 1 EndGAme ENG.pdf
|-- Doc 1 EndGAme FR.pdf
|-- Doc 2 EndGAme EN.html
|-- doc 2 EndGAme FR.html
`-- fire_modules/
```

## Recommended GitHub topics

Add these repository topics in GitHub settings for visibility:

`akai-fire`, `fl-studio`, `midi-controller`, `hardware-script`, `music-production`, `step-sequencer`, `performance-mode`, `python`, `windows`, `piano-roll`

## License

MIT. See [LICENSE](./LICENSE).

## Status

Active custom project by `Kheops74`.

This repository is best understood through the docs rather than a long README, so the README stays intentionally short and points to the full guides.
