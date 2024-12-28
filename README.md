# Modular Polyphonic Synthesizer

A real-time modular polyphonic synthesizer implemented in Python with MIDI support.

## Features
- 16-voice polyphony
- Multiple waveform oscillators (sine, saw, triangle, pulse)
- ADSR envelope per voice
- Low-pass filter with resonance
- Real-time parameter control via MIDI CC
- Live waveform visualization
- Performance monitoring
- Module bypass system

## Installation
```bash
pip install -r requirements.txt
```

## Usage
1. Connect a MIDI device
2. Run the synthesizer:
```bash
cd /path/to/MODULE\ BASED\ SYNTH/src
python main.py
```

## MIDI Control Mapping
- CC 14-17: Oscillator mix levels
- CC 26-29: Oscillator detune
- CC 22: Filter cutoff
- CC 23: Filter resonance
- CC 18-21: ADSR parameters (Attack, Decay, Sustain, Release)

## System Architecture

### Core Components

1. **Audio Engine** (core.py)
   - Voice management system
   - Real-time audio processing
   - Thread-safe parameter updates
   - Audio callback system

2. **Audio Modules** (audio.py)
   - Oscillator generation
   - Filter processing
   - ADSR envelope shaping
   - Signal safety features

3. **MIDI System** (midi.py)
   - MIDI event handling
   - CC mapping and routing
   - Real-time parameter updates

4. **GUI System** (gui.py)
   - Parameter visualization
   - Real-time waveform display
   - Debug controls
   - Performance metrics

5. **Debug System** (debug.py)
   - Performance monitoring
   - Signal flow tracking
   - Module bypass controls
   - Error logging

6. **Configuration** (config.py)
   - Global audio settings
   - MIDI mappings
   - Module state management

### Data Flow
```
MIDI Input → MIDI Handler → State Updates
                            ↓
Audio Callback → Voice Management → Audio Output
                       ↓
                  GUI Updates
```

### Threading Model
- Main Thread: GUI and event handling
- Audio Thread: Real-time audio processing
- MIDI Thread: Event processing
- Update Thread: GUI refresh (30 FPS)

### Performance Specifications
- Buffer size: 256 samples
- Sample rate: 44100 Hz
- Maximum voices: 16
- Update rate: 30 FPS (GUI)
- Control rate: 100 Hz
