"""
Audio Processing Modules
------------------------
Core DSP components for sound synthesis:
- Oscillator: Waveform generation with phase continuity
- Filter: Real-time audio filtering with multiple modes
- ADSR: Envelope generation for amplitude shaping
"""

import numpy as np

class Oscillator:
    """Generates continuous waveforms with phase-correct frequency control"""
    
    def __init__(self):
        self.phase = 0.0  # Keep track of phase for continuous waveform
        self.harmonics_phases = np.zeros(8)  # Track phases for up to 8 harmonics
        
    def generate(self, frequency: float, waveform: str, samples: int, detune: float = 0.0, harmonics: float = 0.0) -> np.ndarray:
        """
        Generate audio samples with optional harmonics
        
        Args:
            frequency: Base frequency in Hz
            waveform: Type of waveform to generate
            samples: Number of samples to generate
            detune: Pitch offset in semitones
            harmonics: Amount of harmonic content (0.0 - 1.0)
        
        Returns:
            np.ndarray: Generated audio samples
        """
        # Ensure phase continuity between buffer generations
        self.phase = self.phase % (2 * np.pi)
        
        # Apply detune using semitone ratio
        detuned_frequency = frequency * (2 ** (detune / 12.0))
        
        # Create time array maintaining phase continuity
        t = np.linspace(self.phase, 
                       self.phase + 2 * np.pi * detuned_frequency * samples / 44100, 
                       samples, 
                       endpoint=False)
        
        # Generate base waveform
        output = self._generate_base_waveform(t, waveform)
        
        # Add harmonics if enabled
        if harmonics > 0:
            for i in range(2, 9):  # Add 2nd through 8th harmonics
                harmonic_t = np.linspace(self.harmonics_phases[i-2],
                                       self.harmonics_phases[i-2] + 2 * np.pi * (detuned_frequency * i) * samples / 44100,
                                       samples,
                                       endpoint=False)
                
                harmonic = self._generate_base_waveform(harmonic_t, waveform)
                output += harmonic * (harmonics / i)  # Decrease amplitude for higher harmonics
                self.harmonics_phases[i-2] = harmonic_t[-1] % (2 * np.pi)
        
        self.phase = t[-1] % (2 * np.pi)
        return output

    def _generate_base_waveform(self, t, waveform):
        """Generate basic waveform without harmonics"""
        if waveform == 'sine':
            return np.sin(t)
        elif waveform == 'saw':
            return 2 * (t / (2 * np.pi) - np.floor(0.5 + t / (2 * np.pi)))
        elif waveform == 'triangle':
            return 2 * np.abs(2 * (t / (2 * np.pi) - np.floor(0.5 + t / (2 * np.pi)))) - 1
        elif waveform == 'pulse':
            return np.where(t % (2 * np.pi) < np.pi, 1.0, -1.0)
        elif waveform == 'noise':
            return np.random.uniform(-1.0, 1.0, size=len(t))  # Generate random noise
        return np.sin(t)  # Default to sine

class Filter:
    """Processes audio through various filter types with adjustable parameters"""
    
    def __init__(self):
        self.cutoff = 1.0  # Start fully open
        self.resonance = 0.0
        self.filter_type = 'lowpass'
        self.steepness = 1.0
        self.harmonics = 0.0
        self.z1 = [0.0, 0.0, 0.0, 0.0]  # Four filter stages
        self.z2 = [0.0, 0.0, 0.0, 0.0]
        self.sample_rate = 44100
        self.min_freq = 20.0    # 20 Hz
        self.max_freq = 22000.0 # 22 kHz
        self.resonance_scale = 5.0  # Increase resonance effect
        self.cutoff_scale = 4.0    # Make cutoff more aggressive

    def set_parameters(self, cutoff, resonance, filter_type, steepness=1.0, harmonics=0.0):
        """Update filter parameters"""
        self.cutoff = np.clip(float(cutoff), 0.01, 0.99)  # Ensure cutoff is float and clipped
        self.resonance = np.clip(float(resonance), 0.0, 0.99)
        self.filter_type = filter_type
        self.steepness = np.clip(float(steepness), 1.0, 4.0)
        self.harmonics = np.clip(float(harmonics), 0.0, 1.0)

    def process(self, signal):
        """Process audio through the filter"""
        # More aggressive frequency scaling
        cutoff_freq = self.min_freq * (self.max_freq / self.min_freq) ** (self.cutoff ** 2)
        
        # Calculate filter coefficients with stronger resonance
        w0 = 2.0 * np.pi * cutoff_freq / self.sample_rate
        cosw0 = np.cos(w0)
        alpha = np.sin(w0) / (2.0 * (1.0 - (self.resonance ** 0.5) * 0.99))  # More aggressive resonance
        
        # Initialize coefficients
        a0 = 1.0 + alpha * self.resonance_scale
        a1 = -2.0 * cosw0
        a2 = 1.0 - alpha * self.resonance_scale
        
        if self.filter_type == 'lowpass':
            b0 = (1.0 - cosw0) / 2.0 * self.cutoff_scale
            b1 = (1.0 - cosw0) * self.cutoff_scale
            b2 = (1.0 - cosw0) / 2.0 * self.cutoff_scale
        elif self.filter_type == 'highpass':
            b0 = (1.0 + cosw0) / 2.0 * self.cutoff_scale
            b1 = -(1.0 + cosw0) * self.cutoff_scale
            b2 = (1.0 + cosw0) / 2.0 * self.cutoff_scale
        elif self.filter_type == 'bandpass':
            b0 = alpha * self.cutoff_scale
            b1 = 0.0
            b2 = -alpha * self.cutoff_scale

        # Normalize coefficients
        b0 /= a0
        b1 /= a0
        b2 /= a0
        a1 /= a0
        a2 /= a0

        # Process signal through multiple filter stages
        output = signal.copy()
        stages = int(self.steepness)
        
        for stage in range(stages):
            temp = np.zeros_like(output)
            for i in range(len(output)):
                # Apply filter with increased effect
                temp[i] = (b0 * output[i] + b1 * self.z1[stage] + b2 * self.z2[stage] 
                          - a1 * self.z1[stage] - a2 * self.z2[stage])
                
                # Update delay line
                self.z2[stage] = self.z1[stage]
                self.z1[stage] = output[i]
            
            output = temp

        # Apply final gain scaling
        output *= (1.0 - self.cutoff * 0.5)  # Reduce volume more as cutoff decreases
        
        return output

class ADSR:
    """ADSR envelope generator with proper release handling"""
    
    def __init__(self):
        self.attack = 0.01
        self.decay = 0.1
        self.sustain = 0.5
        self.release = 0.5
        self.state = 'idle'
        self.current_level = 0.0
        self.release_level = 0.0  # Store level when note is released
        self.sample_rate = 44100
        self.elapsed_samples = 0
        
    def set_parameters(self, attack, decay, sustain, release):
        """Set ADSR parameters in seconds"""
        self.attack = max(0.001, float(attack))  # Minimum 1ms
        self.decay = max(0.001, float(decay))
        self.sustain = max(0.0, min(1.0, float(sustain)))
        self.release = max(0.001, float(release))
        
    def gate_on(self):
        """Trigger attack phase"""
        self.state = 'attack'
        self.elapsed_samples = 0
        
    def gate_off(self):
        """Trigger release phase"""
        if self.state != 'idle':
            self.state = 'release'
            self.release_level = self.current_level  # Store current level for release
            self.elapsed_samples = 0
        
    def process(self, num_samples):
        """Generate envelope samples"""
        output = np.zeros(num_samples)
        
        for i in range(num_samples):
            if self.state == 'idle':
                self.current_level = 0.0
                
            elif self.state == 'attack':
                # Linear attack
                attack_samples = int(self.attack * self.sample_rate)
                if self.elapsed_samples >= attack_samples:
                    self.state = 'decay'
                    self.elapsed_samples = 0
                else:
                    self.current_level = self.elapsed_samples / attack_samples
                    
            elif self.state == 'decay':
                # Exponential decay to sustain level
                decay_samples = int(self.decay * self.sample_rate)
                if self.elapsed_samples >= decay_samples:
                    self.state = 'sustain'
                else:
                    decay_progress = self.elapsed_samples / decay_samples
                    self.current_level = 1.0 + (self.sustain - 1.0) * decay_progress
                    
            elif self.state == 'sustain':
                self.current_level = self.sustain
                
            elif self.state == 'release':
                # Exponential release from current level
                release_samples = int(self.release * self.sample_rate)
                if self.elapsed_samples >= release_samples:
                    self.state = 'idle'
                    self.current_level = 0.0
                else:
                    release_progress = self.elapsed_samples / release_samples
                    self.current_level = self.release_level * (1.0 - release_progress)
            
            output[i] = self.current_level
            self.elapsed_samples += 1
            
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

        def test_noise_wave(self):
            samples = 44100
            waveform = 'noise'
            output = self.oscillator.generate(0, waveform, samples)
            self.assertEqual(len(output), samples)
            self.assertTrue(np.all(output <= 1.0))
            self.assertTrue(np.all(output >= -1.0))

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
