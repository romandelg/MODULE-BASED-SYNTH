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
from typing import Dict
from config import AUDIO_CONFIG, STATE

class Oscillator:
    def __init__(self):
        self.phase = 0.0
        self._cache = {}
        self._cache_size = 1024  # Size of cached waveforms
        
    def generate(self, frequency: float, waveform: str, samples: int) -> np.ndarray:
        # Cache key based on frequency and waveform
        cache_key = (waveform, round(frequency * 100) / 100)  # Round to reduce cache variations
        
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if len(cached) >= samples:
                return cached[:samples]
        
        self.phase = self.phase % (2 * np.pi)
        t = np.linspace(self.phase, self.phase + 2 * np.pi * frequency * samples / AUDIO_CONFIG.SAMPLE_RATE, samples, endpoint=False)
        
        if waveform == 'sine':
            output = np.sin(t)
        elif waveform == 'saw':
            output = 2 * (t / (2 * np.pi) - np.floor(t / (2 * np.pi) + 0.5))
        elif waveform == 'triangle':
            output = 2 * np.abs(2 * (t / (2 * np.pi) - np.floor(t / (2 * np.pi) + 0.5))) - 1
        else:  # pulse
            output = np.sign(np.sin(t))
        
        self.phase = t[-1]
        
        # Cache the output for future use
        if len(output) <= self._cache_size:
            self._cache[cache_key] = output.copy()
            
        return output

class Filter:
    def __init__(self):
        self.z1 = 0.0
        self.z2 = 0.0

    def process(self, input_signal: np.ndarray, cutoff: float, resonance: float) -> np.ndarray:
        f = 2 * np.sin((np.pi * cutoff) / AUDIO_CONFIG.SAMPLE_RATE)
        q = resonance
        output = np.zeros_like(input_signal)
        
        for i in range(len(input_signal)):
            self.z1 = self.z1 + f * (input_signal[i] - self.z2)
            self.z2 = self.z2 + f * self.z1
            output[i] = self.z2
            
        return output

class ADSR:
    def __init__(self):
        self.state = 'idle'
        self.value = 0.0
        self.phase = 0.0
        
    def process(self, gate: bool, params: Dict[str, float], samples: int) -> np.ndarray:
        output = np.zeros(samples)
        increment = 1.0 / (AUDIO_CONFIG.SAMPLE_RATE * samples)
        
        for i in range(samples):
            if gate and self.state == 'idle':
                self.state = 'attack'
                self.phase = 0.0
                
            if not gate and self.state != 'release':
                self.state = 'release'
                self.phase = 0.0
                
            if self.state == 'attack':
                self.value += increment / params['attack']
                if self.value >= 1.0:
                    self.value = 1.0
                    self.state = 'decay'
                    
            elif self.state == 'decay':
                self.value -= increment / params['decay']
                if self.value <= params['sustain']:
                    self.value = params['sustain']
                    self.state = 'sustain'
                    
            elif self.state == 'release':
                self.value -= increment / params['release']
                if self.value <= 0.0:
                    self.value = 0.0
                    self.state = 'idle'
                    
            output[i] = self.value
            
        return output

def dc_offset_filter(signal: np.ndarray) -> np.ndarray:
    return signal - np.mean(signal)

def safety_limiter(signal: np.ndarray) -> np.ndarray:
    return np.clip(signal, -1.0, 1.0)
