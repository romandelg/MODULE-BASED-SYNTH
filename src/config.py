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
        self.filter_steepness = 1.0  # Initialize filter steepness (1-4 stages)
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
        self.input_source = 'midi'  # 'midi' for live notes, 'sequencer' for sequencer playback
        self.sequencer_enabled = False
        self.sequencer_notes = [60, 64, 67, 72]  # C4, E4, G4, C5
        self.sequencer_recording = False
        self.sequencer_record_count = 0
        
        # Effects parameters
        self.fx_reverb = 0.0
        self.fx_delay = 0.0
        self.fx_delay_time = 0.3  # 300ms default delay time
        self.fx_reverb_size = 0.5  # Room size
        self.fx_reverb_damping = 0.5  # Damping factor
        
        # Update available effects list
        self.available_fx = ['none', 'chorus', 'flanger', 'phaser', 'reverb', 'delay', 'distortion']
        
        # Default parameters for each effect type
        self.fx_defaults = {
            'chorus': {'depth': 0.5, 'rate': 1.2, 'mix': 0.5},
            'flanger': {'depth': 0.7, 'rate': 0.5, 'mix': 0.5},
            'phaser': {'depth': 0.6, 'rate': 0.4, 'mix': 0.5},
            'reverb': {'depth': 0.5, 'rate': 0.8, 'mix': 0.3},
            'delay': {'depth': 0.5, 'rate': 0.3, 'mix': 0.4},
            'distortion': {'depth': 0.3, 'rate': 1.0, 'mix': 0.5}
        }
        
        # Initialize effect slots with default parameters
        self.fx_slots = [{
            'type': 'none',
            'depth': 0.5,
            'rate': 1.0,
            'mix': 0.5
        } for _ in range(3)]
        
        # Chain states
        self.chain_enabled = {
            'signal': True,
            'oscillators': True,
            'noise_sub': True,
            'mixer': True,
            'envelope': True,
            'filter': True,
            'lfo': True,
            'effects': True,  # Change to True
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
            'effects': False,  # Change to False
            'amp': False
        }
        
        self.compressor_threshold = 0.5
        self.compressor_ratio = 4.0
        self.compressor_attack = 0.01
        self.compressor_release = 0.1
        self.saturation_drive = 1.0
        self.saturation_bypass = False
        self.harmonizer_shift = 0

# Global configuration instances
AUDIO_CONFIG = AudioConfig()
MIDI_CONFIG = MIDIConfig()
STATE = ModuleState()
