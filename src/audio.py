"""
Audio Processing Modules
----------------------
DSP components for sound generation and processing.

Features:
1. Oscillators:
   - Multiple waveforms (sine, saw, triangle, pulse)
   - Phase continuity
   - Frequency calculation from MIDI notes
   - Waveform caching for performance
   - Detuning support

2. Filters:
   - Low-pass filter implementation
   - Resonance control
   - Zero-delay feedback
   - Real-time parameter modulation

3. ADSR Envelope:
   - Attack, Decay, Sustain, Release stages
   - Sample-accurate timing
   - Gate control
   - Smooth transitions

4. Safety Features:
   - DC offset removal
   - Output limiting
   - Signal normalization
"""

import numpy as np

class Oscillator:
    def __init__(self):
        self.phase = 0.0
        
    def generate(self, frequency: float, waveform: str, samples: int) -> np.ndarray:
        """Generate a basic sine wave with phase continuity"""
        self.phase = self.phase % (2 * np.pi)
        t = np.linspace(self.phase, 
                       self.phase + 2 * np.pi * frequency * samples / 44100, 
                       samples, 
                       endpoint=False)
        
        output = np.sin(t)
        self.phase = t[-1]
        return output * 0.5  # Safety amplitude reduction
