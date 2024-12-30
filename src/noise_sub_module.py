"""
Sub-Oscillator Module
---------------------
Generates sub-oscillator signals and mixes them with the main oscillator signal.
Includes controls for sub-oscillator amount, harmonics, and inharmonicity.
"""

import numpy as np
from config import STATE

class SubOscillatorModule:
    """Generates sub-oscillator signals and mixes them with the main oscillator signal"""
    
    def __init__(self):
        self.sub_amount = 0.0
        self.harmonics = 0.0
        self.inharmonicity = 0.0
        self.sample_rate = 44100

    def set_parameters(self, sub_amount, harmonics, inharmonicity):
        """Set parameters for sub-oscillator generation"""
        self.sub_amount = sub_amount
        self.harmonics = harmonics
        self.inharmonicity = inharmonicity

    def generate(self, main_signal, frequency, frames):
        """Generate sub-oscillator signals and mix them with the main signal"""
        sub_osc = np.sin(2 * np.pi * (frequency / 2) * np.arange(frames) / self.sample_rate) * self.sub_amount
        
        # Add harmonics to the main signal
        if self.harmonics > 0:
            for i in range(2, 9):  # Add 2nd through 8th harmonics
                harmonic = np.sin(2 * np.pi * (frequency * i) * np.arange(frames) / self.sample_rate)
                main_signal += harmonic * (self.harmonics / i)
        
        # Apply inharmonicity
        if self.inharmonicity > 0:
            inharmonic = np.sin(2 * np.pi * (frequency * (1 + self.inharmonicity)) * np.arange(frames) / self.sample_rate)
            main_signal += inharmonic * self.inharmonicity
        
        return main_signal + sub_osc

class NoiseSubModule:
    def __init__(self):
        self.noise_level = 0.0
        self.sub_amount = 0.0
        self.harmonics = 0.0
        self.inharmonicity = 0.0
        self.sample_rate = 44100

    def set_parameters(self, noise_amount=0.0, sub_amount=0.0, harmonics=0.0, inharmonicity=0.0):
        self.noise_level = noise_amount
        self.sub_amount = sub_amount
        self.harmonics = harmonics
        self.inharmonicity = inharmonicity

    def generate(self, main_signal, frequency, frames):
        """Generate noise and mix with the input signal"""
        # Generate white noise
        noise = np.random.normal(0, 1, frames) * self.noise_level
        
        # Generate sub-oscillator
        if self.sub_amount > 0:
            sub_osc = np.sin(2 * np.pi * (frequency / 2) * np.arange(frames) / self.sample_rate) * self.sub_amount
            main_signal = main_signal + sub_osc
            
        # Add harmonics
        if self.harmonics > 0:
            for i in range(2, 5):
                harmonic = np.sin(2 * np.pi * (frequency * i) * np.arange(frames) / self.sample_rate)
                main_signal += harmonic * (self.harmonics / i)
                
        # Apply inharmonicity
        if self.inharmonicity > 0:
            inharmonic = np.sin(2 * np.pi * (frequency * (1 + self.inharmonicity)) * np.arange(frames) / self.sample_rate)
            main_signal += inharmonic * self.inharmonicity
            
        return main_signal + noise
