"""
Configuration Management
----------------------
Global settings and state management.

Features:
1. Audio Settings:
   - Sample rate configuration
   - Buffer size management
   - Voice count limits
   - Latency control

2. MIDI Configuration:
   - Control change mappings
   - Parameter ranges
   - Device settings

3. Module State:
   - Oscillator parameters
   - Filter settings
   - ADSR values
   - Bypass states

4. Performance Settings:
   - Update rates
   - Buffer sizes
   - Threading parameters
   - Debug flags
"""

from dataclasses import dataclass
from typing import Dict, Any
import numpy as np

@dataclass
class AudioConfig:
    SAMPLE_RATE: int = 44100
    BUFFER_SIZE: int = 1024
    MAX_VOICES: int = 1       # Single voice
    CONTROL_RATE: int = 30
    LATENCY: float = 'high'
    USE_DOUBLE: bool = False

@dataclass
class MIDIConfig:
    # MIDI CC mappings
    OSC_MIX_CCS: tuple = (14, 15, 16, 17)
    OSC_DETUNE_CCS: tuple = (26, 27, 28, 29)
    FILTER_CUTOFF_CC: int = 22
    FILTER_RES_CC: int = 23
    ADSR_CCS: tuple = (18, 19, 20, 21)

class ModuleState:
    def __init__(self):
        self.osc_mix = np.ones(4) * 0.25
        self.osc_detune = np.zeros(4)
        self.filter_cutoff = 1.0
        self.filter_res = 0.0
        self.adsr = {
            'attack': 0.1,
            'decay': 0.1,
            'sustain': 0.7,
            'release': 0.3
        }
        self.bypass = {
            'oscillators': False,
            'filter': False,
            'adsr': False
        }

AUDIO_CONFIG = AudioConfig()
MIDI_CONFIG = MIDIConfig()
STATE = ModuleState()
