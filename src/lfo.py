"""
LFO (Low-Frequency Oscillator) Module
-------------------------------------
Generates LFO waveforms and routes them to parameters.
"""

import numpy as np
from config import STATE, AUDIO_CONFIG

# Update PARAMETER_RANGES
PARAMETER_RANGES = {
    'cutoff': (20, 20000),
    'resonance': (0, 100),
    'volume': (0, 100),
    'pan': (-100, 100),
    'pitch': (-12, 12),  # semitones
    'filter_env': (0, 100),
    'amp_env': (0, 100),
    'osc1_level': (0, 100),
    'osc2_level': (0, 100),
    'osc3_level': (0, 100),
    'sub_level': (0, 100),
    'noise_level': (0, 100)
}

class LFO:
    """Generates LFO waveforms and routes them to parameters"""
    
    def __init__(self, frequency=1.0, waveform='sine', offset=0.0, depth=1.0):
        self.frequency = frequency
        self.waveform = waveform
        self.offset = offset
        self.depth = np.clip(depth, 0, 1)  # Normalize depth to 0-1
        self.phase = 0.0
        self.enabled = True
        self.bypassed = False
        self.sample_rate = AUDIO_CONFIG.SAMPLE_RATE
        self.targets = {}  # Dictionary to store {param_name: (base_value, param_type)}
        self.current_value = 0.0
        self.last_time = 0
        self.viz_buffer_size = 1000
        self.viz_buffer = np.zeros(self.viz_buffer_size)
        self.viz_index = 0

    def set_parameters(self, frequency, waveform, offset, depth):
        """Set LFO parameters"""
        self.frequency = frequency
        self.waveform = waveform
        self.offset = offset
        self.depth = np.clip(depth, 0, 1)

    def add_target(self, target_name, base_value):
        """Add or update a modulation target"""
        self.targets[target_name] = (base_value, target_name)

    def remove_target(self, target_name):
        """Remove a target parameter"""
        if target_name in self.targets:
            del self.targets[target_name]

    def _scale_value(self, raw_value, param_type):
        """Scale raw LFO value (-1 to 1) to parameter range"""
        if param_type not in PARAMETER_RANGES:
            return raw_value
            
        min_val, max_val = PARAMETER_RANGES[param_type]
        center = (max_val + min_val) / 2
        range_half = (max_val - min_val) / 2
        
        # Scale the raw value (-1 to 1) to parameter range
        scaled = center + (raw_value * range_half * self.depth)
        return np.clip(scaled, min_val, max_val)

    def process(self):
        """Process LFO and update target parameters"""
        if not self.enabled or self.bypassed:
            return
            
        # Generate basic LFO value
        if self.waveform == 'sine':
            value = np.sin(2 * np.pi * self.phase)
        elif self.waveform == 'triangle':
            value = 2 * abs(2 * (self.phase - np.floor(self.phase + 0.5))) - 1
        elif self.waveform == 'square':
            value = np.sign(np.sin(2 * np.pi * self.phase))
        else:  # saw
            value = 2 * (self.phase - np.floor(self.phase)) - 1
            
        # Update phase
        self.phase += self.frequency / self.sample_rate
        if self.phase >= 1.0:
            self.phase -= 1.0
            
        # Apply depth and offset
        value = value * self.depth + self.offset
        
        # Update target parameters
        for target_name, (base_value, param_type) in self.targets.items():
            if hasattr(STATE, target_name):
                # Get parameter range
                min_val, max_val = PARAMETER_RANGES[param_type]
                
                # Scale LFO value to parameter range
                param_range = max_val - min_val
                center = base_value
                modulation = (value * param_range * self.depth) / 2
                new_value = np.clip(center + modulation, min_val, max_val)
                
                # Update parameter in STATE
                setattr(STATE, target_name, new_value)

    def generate(self, buffer_size):
        """Generate LFO samples for audio buffer"""
        if self.bypassed:
            return np.zeros(buffer_size)

        # Calculate time points for this buffer
        t = np.linspace(self.phase, 
                       self.phase + (self.frequency * buffer_size / self.sample_rate),
                       buffer_size, endpoint=False)

        # Generate waveform
        if self.waveform == 'sine':
            values = np.sin(2 * np.pi * t)
        elif self.waveform == 'triangle':
            values = 2 * np.abs(2 * (t - np.floor(t + 0.5))) - 1
        elif self.waveform == 'square':
            values = np.sign(np.sin(2 * np.pi * t))
        else:  # saw
            values = 2 * (t - np.floor(t)) - 1

        # Update phase for next buffer
        self.phase = t[-1]
        while self.phase >= 1.0:
            self.phase -= 1.0

        # Apply depth and offset
        values = values * self.depth + self.offset

        # Update parameters
        for target_name, (base_value, param_type) in self.targets.items():
            if hasattr(STATE, target_name):
                scaled = self._scale_value(values[-1], param_type)
                setattr(STATE, target_name, scaled)

        return values

    def get_waveform(self, t):
        """Get waveform values for visualization"""
        if self.waveform == 'sine':
            return np.sin(2 * np.pi * t) * self.depth + self.offset
        elif self.waveform == 'triangle':
            return (2 * np.abs(2 * (t - np.floor(t + 0.5))) - 1) * self.depth + self.offset
        elif self.waveform == 'square':
            return np.sign(np.sin(2 * np.pi * t)) * self.depth + self.offset
        else:
            return (2 * (t - np.floor(t)) - 1) * self.depth + self.offset

    def get_value(self):
        """Get current normalized LFO value (-1 to 1)"""
        if self.bypassed:
            return 0.0
            
        t = self.phase
        if self.waveform == 'sine':
            value = np.sin(2 * np.pi * t)
        elif self.waveform == 'triangle':
            value = 2 * np.abs(2 * (t - np.floor(t + 0.5))) - 1
        elif self.waveform == 'square':
            value = np.sign(np.sin(2 * np.pi * t))
        else:  # saw
            value = 2 * (t - np.floor(t)) - 1
            
        return value * self.depth + self.offset

    def enable(self):
        """Enable the LFO"""
        self.enabled = True

    def disable(self):
        """Disable the LFO"""
        self.enabled = False

    def bypass(self):
        """Bypass the LFO"""
        self.bypassed = True

    def unbypass(self):
        """Unbypass the LFO"""
        self.bypassed = False

    def get_visualization_data(self):
        """Generate visualization data for GUI"""
        if self.bypassed:
            return np.zeros(self.viz_buffer_size)
            
        t = np.linspace(0, 1, self.viz_buffer_size)
        
        if self.waveform == 'sine':
            values = np.sin(2 * np.pi * t)
        elif self.waveform == 'triangle':
            values = 2 * np.abs(2 * (t - np.floor(t + 0.5))) - 1
        elif self.waveform == 'square':
            values = np.sign(np.sin(2 * np.pi * t))
        else:  # saw
            values = 2 * (t - np.floor(t)) - 1
            
        return values * self.depth + self.offset

    def update_visualization(self):
        """Update visualization buffer with current values"""
        self.viz_buffer = self.get_visualization_data()
        return self.viz_buffer
