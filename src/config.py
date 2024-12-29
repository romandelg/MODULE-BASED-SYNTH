"""
Configuration Management
------------------------
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
    OSC_MIX_CCS: Tuple[int, ...] = (14, 15, 16, 17, 18)  # Add 5th oscillator
    OSC_DETUNE_CCS: Tuple[int, ...] = (26, 27, 28, 29, 30)  # Add 5th oscillator
    FILTER_CUTOFF_CC: int = 22
    FILTER_RES_CC: int = 23
    ADSR_CCS: Tuple[int, ...] = (18, 19, 20, 21)

class ModuleState:
    """State management for synthesizer modules"""
    
    def __init__(self):
        self.osc_mix = np.ones(5) * 0.2  # Update to size 5
        self.osc_detune = np.zeros(5)  # Update to size 5
        self.osc_harmonics = np.zeros(5)  # Update to size 5
        self.osc_waveforms = ['sine', 'saw', 'triangle', 'pulse', 'noise']  # Add noise waveform
        self.filter_cutoff = 1.0
        self.filter_res = 0.0
        self.filter_type = 'lowpass'
        self.filter_steepness = 1.0  # Number of filter stages (1-4)
        self.filter_harmonics = 0.0  # Amount of harmonic enhancement (0-1)
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
        self.lfo_depth = 1.0  # Initialize with default depth
        
        # Noise and Sub-Oscillator Module parameters
        self.noise_amount = 0.0
        self.sub_amount = 0.0
        self.noise_harmonics = 0.0
        self.noise_inharmonicity = 0.0
        
        # Signal chain settings
        self.input_source = 'midi'  # Add before chain_enabled
        self.sequencer_enabled = False
        self.sequencer_notes = [60, 64, 67, 72]  # C4, E4, G4, C5
        
        # Chain states
        self.chain_enabled = {
            'signal': True,
            'oscillators': True,
            'noise_sub': True,
            'mixer': True,
            'envelope': True,
            'filter': True,
            'lfo': True,
            'effects': False,
            'amp': True
        }
        
        self.chain_bypass = {
            'signal': False,
            'oscillators': False,
            'noise_sub': False,
            'mixer': False,
            'envelope': False,
            'filter': False,
            'lfo': False,
            'effects': True,
            'amp': False
        }

# Global configuration instances
AUDIO_CONFIG = AudioConfig()
MIDI_CONFIG = MIDIConfig()
STATE = ModuleState()
