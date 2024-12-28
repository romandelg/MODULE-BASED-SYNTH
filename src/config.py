"""
Configuration Management
----------------------
Defines configuration parameters and state management for the synthesizer.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np

@dataclass
class AudioConfig:
    """Audio configuration parameters"""
    SAMPLE_RATE: int = 44100
    BUFFER_SIZE: int = 1024
    MAX_VOICES: int = 16

@dataclass
class MIDIConfig:
    """MIDI control change mappings"""
    OSC_MIX_CCS: Tuple[int, ...] = (14, 15, 16, 17)
    OSC_DETUNE_CCS: Tuple[int, ...] = (26, 27, 28, 29)
    FILTER_CUTOFF_CC: int = 22
    FILTER_RES_CC: int = 23
    ADSR_CCS: Tuple[int, ...] = (18, 19, 20, 21)

class ModuleState:
    """State management for synthesizer modules"""
    
    def __init__(self):
        self.osc_mix = np.ones(4) * 0.25
        self.osc_detune = np.zeros(4)
        self.osc_waveforms = ['sine', 'saw', 'triangle', 'pulse']
        self.filter_cutoff = 1.0
        self.filter_res = 0.0
        self.filter_type = 'lowpass'
        self.adsr = {
            'attack': 0.01,
            'decay': 0.1,
            'sustain': 0.7,
            'release': 0.3
        }
        self.master_gain = 1.0
        self.master_pan = 0.0  # -1.0 (left) to 1.0 (right)
        self.lfo_frequency = 1.0
        self.lfo_waveform = 'sine'
        self.lfo_offset = 0.0
        self.lfo_depth = 1.0

# Global configuration instances
AUDIO_CONFIG = AudioConfig()
MIDI_CONFIG = MIDIConfig()
STATE = ModuleState()
