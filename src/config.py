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

from dataclasses import dataclass, field
from typing import Dict, Any, List, Tuple, Optional  # Add Optional import
import numpy as np

@dataclass
class AudioConfig:
    # Basic audio settings
    SAMPLE_RATE: int = 44100
    BUFFER_SIZE: int = 1024
    MAX_VOICES: int = 16  # Set to 16 for polyphony
    
    # Latency settings
    LATENCY_MODE: str = 'high'  # 'low', 'medium', 'high'
    LATENCY_MS: Dict[str, float] = field(default_factory=lambda: {
        'low': 10.0,
        'medium': 20.0,
        'high': 30.0
    })
    
    # Buffer management
    MIN_BUFFER_SIZE: int = 256
    MAX_BUFFER_SIZE: int = 2048
    BUFFER_SIZES: List[int] = field(default_factory=lambda: [256, 512, 1024, 2048])
    
    # Performance settings
    CONTROL_RATE: int = 100  # Hz
    UPDATE_RATE: int = 30   # GUI refresh rate
    VOICE_LIMIT: bool = True
    CPU_LIMIT: float = 0.8  # 80% CPU limit

@dataclass
class MIDIConfig:
    # CC ranges and mappings
    OSC_MIX_CCS: Tuple[int, ...] = (14, 15, 16, 17)
    OSC_DETUNE_CCS: Tuple[int, ...] = (26, 27, 28, 29)
    OSC_WAVEFORM_CCS: Tuple[int, ...] = (30, 31, 32, 33)
    FILTER_CUTOFF_CC: int = 22
    FILTER_RES_CC: int = 23
    FILTER_TYPE_CC: int = 24
    ADSR_CCS: Tuple[int, ...] = (18, 19, 20, 21)
    
    # Parameter ranges
    CC_RESOLUTION: int = 127
    PITCH_BEND_RANGE: int = 2  # semitones
    
    # Device settings
    DEFAULT_INPUT_NAME: str = None
    CHANNEL_FILTER: Optional[int] = None
    
    # CC value ranges
    PARAMETER_RANGES: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        'osc_mix': (0.0, 1.0),
        'osc_detune': (-12.0, 12.0),
        'filter_cutoff': (20.0, 20000.0),
        'filter_res': (0.0, 0.99),
        'adsr_attack': (0.001, 2.0),
        'adsr_decay': (0.001, 2.0),
        'adsr_sustain': (0.0, 1.0),
        'adsr_release': (0.001, 3.0)
    })

class ModuleState:
    def __init__(self):
        # Oscillator parameters
        self.osc_mix = np.ones(4) * 0.25
        self.osc_detune = np.zeros(4)
        self.osc_waveforms = ['sine', 'saw', 'triangle', 'pulse']
        self.osc_sync = False
        
        # Filter parameters
        self.filter_cutoff = 1.0
        self.filter_res = 0.0
        self.filter_type = 'lowpass'
        self.filter_tracking = 1.0  # Key tracking amount
        
        # Envelope parameters
        self.adsr = {
            'attack': 0.01,
            'decay': 0.1,
            'sustain': 0.7,
            'release': 0.3
        }
        
        # Module bypass and states
        self.bypass = {
            'oscillators': False,
            'filter': False,
            'adsr': False
        }
        
        # Performance states
        self.cpu_load = 0.0
        self.active_voices = 0
        self.peak_level = 0.0
        
        # Debug states
        self.debug_flags = {
            'log_midi': True,
            'log_audio': False,
            'log_cpu': True,
            'monitor_signals': True
        }
        
    def normalize_parameter(self, module: str, param: str, value: float) -> float:
        """Normalize parameter value to valid range"""
        ranges = MIDI_CONFIG.PARAMETER_RANGES
        if f"{module}_{param}" in ranges:
            min_val, max_val = ranges[f"{module}_{param}"]
            return np.clip(value, min_val, max_val)
        return value
        
    def update_parameter(self, module: str, param: str, value: float):
        """Thread-safe parameter update with validation"""
        value = self.normalize_parameter(module, param, value)
        if hasattr(self, module):
            if isinstance(getattr(self, module), dict):
                getattr(self, module)[param] = value
            elif isinstance(getattr(self, module), np.ndarray):
                idx = int(param)
                getattr(self, module)[idx] = value

# Global instances
AUDIO_CONFIG = AudioConfig()
MIDI_CONFIG = MIDIConfig()
STATE = ModuleState()

# Performance monitoring thresholds
PERF_THRESHOLDS = {
    'cpu_warning': 0.7,    # 70% CPU usage
    'cpu_critical': 0.9,   # 90% CPU usage
    'latency_warning': 15, # 15ms latency
    'buffer_underruns': 5  # Max underruns before warning
}
