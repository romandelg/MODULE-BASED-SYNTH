"""
Noise and Sub-Oscillator Module
-------------------------------
Generates sub-oscillator signals and mixes them with the main oscillator signal.
"""

import numpy as np

class NoiseSubModule:
    """Generates sub-oscillator signals and mixes them with the main oscillator signal"""
    
    def __init__(self):
        self.noise_amount = 0.0
        self.sub_amount = 0.0
        self.harmonics = 0.0
        self.inharmonicity = 0.0

    def set_parameters(self, noise_amount, sub_amount, harmonics, inharmonicity):
        """Set parameters for noise and sub-oscillator generation"""
        self.noise_amount = noise_amount
        self.sub_amount = sub_amount
        self.harmonics = harmonics
        self.inharmonicity = inharmonicity

    def generate(self, signal, frequency, frames):
        """Generate noise and sub-oscillator signals and mix them with the main signal"""
        noise = np.random.uniform(-1.0, 1.0, frames) * self.noise_amount
        sub_osc = np.sin(2 * np.pi * (frequency / 2) * np.arange(frames) / 44100) * self.sub_amount
        
        # Add harmonics to the sub-oscillator
        for i in range(2, 9):
            harmonic_freq = frequency / 2 * i * (1 + self.inharmonicity)
            sub_osc += np.sin(2 * np.pi * harmonic_freq * np.arange(frames) / 44100) * (self.harmonics / i)
        
        return signal + noise + sub_osc
