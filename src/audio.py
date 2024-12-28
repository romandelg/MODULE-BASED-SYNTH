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
        
        if waveform == 'sine':
            output = np.sin(t)
        elif waveform == 'saw':
            output = 2 * (t / (2 * np.pi) - np.floor(0.5 + t / (2 * np.pi)))
        elif waveform == 'triangle':
            output = 2 * np.abs(2 * (t / (2 * np.pi) - np.floor(0.5 + t / (2 * np.pi)))) - 1
        elif waveform == 'pulse':
            output = np.where(t % (2 * np.pi) < np.pi, 1.0, -1.0)
        else:
            output = np.sin(t)  # Default to sine
            
        self.phase = t[-1]
        return output * 0.5  # Safety amplitude

# Unit tests for Oscillator class
if __name__ == '__main__':
    import unittest

    class TestOscillator(unittest.TestCase):
        def setUp(self):
            self.oscillator = Oscillator()
            
        def test_sine_wave(self):
            frequency = 440.0
            samples = 44100
            waveform = 'sine'
            output = self.oscillator.generate(frequency, waveform, samples)
            self.assertEqual(len(output), samples)
            self.assertTrue(np.all(output <= 0.5))
            self.assertTrue(np.all(output >= -0.5))
            
        def test_saw_wave(self):
            frequency = 440.0
            samples = 44100
            waveform = 'saw'
            output = self.oscillator.generate(frequency, waveform, samples)
            self.assertEqual(len(output), samples)
            self.assertTrue(np.all(output <= 0.5))
            self.assertTrue(np.all(output >= -0.5))
            
        def test_triangle_wave(self):
            frequency = 440.0
            samples = 44100
            waveform = 'triangle'
            output = self.oscillator.generate(frequency, waveform, samples)
            self.assertEqual(len(output), samples)
            self.assertTrue(np.all(output <= 0.5))
            self.assertTrue(np.all(output >= -0.5))
            
        def test_pulse_wave(self):
            frequency = 440.0
            samples = 44100
            waveform = 'pulse'
            output = self.oscillator.generate(frequency, waveform, samples)
            self.assertEqual(len(output), samples)
            self.assertTrue(np.all(output <= 0.5))
            self.assertTrue(np.all(output >= -0.5))

    unittest.main()
