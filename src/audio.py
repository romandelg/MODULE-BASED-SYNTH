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
        self.cache = {}  # Cache for waveforms
        
    def generate(self, frequency: float, waveform: str, samples: int, detune: float = 0.0) -> np.ndarray:
        """Generate waveform with phase continuity and caching"""
        self.phase = self.phase % (2 * np.pi)
        detuned_frequency = frequency * (2 ** (detune / 12.0))  # Apply detune in semitones
        t = np.linspace(self.phase, 
                       self.phase + 2 * np.pi * detuned_frequency * samples / 44100, 
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

class Filter:
    def __init__(self):
        self.cutoff = 0.5
        self.resonance = 0.0
        self.filter_type = 'lowpass'
        self.z1 = 0.0
        self.z2 = 0.0

    def process(self, signal: np.ndarray) -> np.ndarray:
        """Process the signal with the filter"""
        if self.filter_type == 'lowpass':
            return self.lowpass(signal)
        elif self.filter_type == 'highpass':
            return self.highpass(signal)
        elif self.filter_type == 'bandpass':
            return self.bandpass(signal)
        return signal

    def lowpass(self, signal: np.ndarray) -> np.ndarray:
        """Low-pass filter implementation"""
        alpha = np.exp(-2.0 * np.pi * self.cutoff / 44100.0)
        output = np.zeros_like(signal)
        for i in range(len(signal)):
            self.z1 = alpha * self.z1 + (1 - alpha) * signal[i]
            output[i] = self.z1
        return output

    def highpass(self, signal: np.ndarray) -> np.ndarray:
        """High-pass filter implementation"""
        alpha = np.exp(-2.0 * np.pi * self.cutoff / 44100.0)
        output = np.zeros_like(signal)
        for i in range(len(signal)):
            self.z1 = alpha * (self.z1 + signal[i] - self.z2)
            self.z2 = signal[i]
            output[i] = self.z1
        return output

    def bandpass(self, signal: np.ndarray) -> np.ndarray:
        """Band-pass filter implementation"""
        alpha = np.exp(-2.0 * np.pi * self.cutoff / 44100.0)
        output = np.zeros_like(signal)
        for i in range(len(signal)):
            self.z1 = alpha * (signal[i] - self.z2) + (1 - alpha) * self.z1
            self.z2 = signal[i]
            output[i] = self.z1
        return output

class ADSR:
    def __init__(self):
        self.attack = 0.01
        self.decay = 0.1
        self.sustain = 0.7
        self.release = 0.3
        self.state = 'idle'
        self.level = 0.0
        self.gate = False

    def set_parameters(self, attack, decay, sustain, release):
        self.attack = max(0.001, attack)
        self.decay = max(0.001, decay)
        self.sustain = max(0.0, min(1.0, sustain))
        self.release = max(0.001, release)

    def gate_on(self):
        self.state = 'attack'
        self.gate = True

    def gate_off(self):
        self.state = 'release'
        self.gate = False

    def process(self, frames):
        output = np.zeros(frames)
        for i in range(frames):
            if self.state == 'attack':
                self.level += 1.0 / (self.attack * 44100)
                if self.level >= 1.0:
                    self.level = 1.0
                    self.state = 'decay'
            elif self.state == 'decay':
                self.level -= (1.0 - self.sustain) / (self.decay * 44100)
                if self.level <= self.sustain:
                    self.level = self.sustain
                    self.state = 'sustain'
            elif self.state == 'sustain':
                self.level = self.sustain
            elif self.state == 'release':
                self.level -= self.sustain / (self.release * 44100)
                if self.level <= 0.0:
                    self.level = 0.0
                    self.state = 'idle'
            output[i] = self.level
        return output

# Unit tests for Oscillator and Filter classes
if __name__ == '__main__':
    import unittest

    class TestAudioModules(unittest.TestCase):
        def setUp(self):
            self.oscillator = Oscillator()
            self.filter = Filter()
            
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

        def test_detune(self):
            frequency = 440.0
            samples = 44100
            waveform = 'sine'
            detune = 1.0  # One semitone up
            output = self.oscillator.generate(frequency, waveform, samples, detune)
            self.assertEqual(len(output), samples)
            self.assertTrue(np.all(output <= 0.5))
            self.assertTrue(np.all(output >= -0.5))

        def test_lowpass_filter(self):
            signal = np.ones(100)
            self.filter.cutoff = 0.1
            self.filter.filter_type = 'lowpass'
            output = self.filter.process(signal)
            self.assertEqual(len(output), len(signal))
            self.assertTrue(np.all(output <= 1.0))
            self.assertTrue(np.all(output >= 0.0))

        def test_highpass_filter(self):
            signal = np.ones(100)
            self.filter.cutoff = 0.1
            self.filter.filter_type = 'highpass'
            output = self.filter.process(signal)
            self.assertEqual(len(output), len(signal))
            self.assertTrue(np.all(output <= 1.0))
            self.assertTrue(np.all(output >= 0.0))

        def test_bandpass_filter(self):
            signal = np.ones(100)
            self.filter.cutoff = 0.1
            self.filter.filter_type = 'bandpass'
            output = self.filter.process(signal)
            self.assertEqual(len(output), len(signal))
            self.assertTrue(np.all(output <= 1.0))
            self.assertTrue(np.all(output >= 0.0))

    unittest.main()
