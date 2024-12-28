"""
LFO (Low-Frequency Oscillator) Module
----------------------
Generates LFO waveforms and routes them to various parameters.
"""

import numpy as np
from config import STATE  # Import STATE for parameter updates

class LFO:
    """Generates LFO waveforms and routes them to parameters"""
    
    def __init__(self, frequency=1.0, waveform='sine', offset=0.0, depth=1.0):
        self.frequency = frequency
        self.waveform = waveform
        self.offset = offset
        self.depth = depth
        self.phase = 0.0
        self.enabled = True
        self.bypassed = False
        self.sample_rate = 44100
        self.targets = {}  # Dictionary to map LFO output to parameters

    def set_parameters(self, frequency, waveform, offset, depth):
        self.frequency = frequency
        self.waveform = waveform
        self.offset = offset
        self.depth = depth

    def add_target(self, target_name, base_value):
        """Add a target parameter to modulate"""
        self.targets[target_name] = base_value

    def remove_target(self, target_name):
        """Remove a target parameter"""
        if target_name in self.targets:
            del self.targets[target_name]

    def generate(self, frames):
        """Generate LFO waveform and apply modulation to targets"""
        if not self.enabled:
            return np.zeros(frames)

        t = np.arange(frames) / self.sample_rate
        t += self.offset  # Apply timing offset
        if self.waveform == 'sine':
            lfo_output = np.sin(2 * np.pi * self.frequency * t + self.phase)
        elif self.waveform == 'triangle':
            lfo_output = 2 * np.abs(2 * (t * self.frequency - np.floor(t * self.frequency + 0.5))) - 1
        elif self.waveform == 'square':
            lfo_output = np.sign(np.sin(2 * np.pi * self.frequency * t + self.phase))
        elif self.waveform == 'saw':
            lfo_output = 2 * (t * self.frequency - np.floor(t * self.frequency + 0.5))
        else:
            lfo_output = np.zeros(frames)

        self.phase += 2 * np.pi * self.frequency * frames / self.sample_rate
        self.phase %= 2 * np.pi

        if not self.bypassed:
            for target_name, base_value in self.targets.items():
                modulated_value = base_value + lfo_output * self.depth  # Apply modulation depth
                setattr(STATE, target_name, modulated_value)

        return lfo_output  # Return the generated LFO waveform

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def bypass(self):
        self.bypassed = True

    def unbypass(self):
        self.bypassed = False
