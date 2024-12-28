"""
Core Synthesizer Engine
----------------------
Main audio processing and voice management system.

Features:
- Polyphonic voice handling with voice stealing
- Real-time audio generation
- Thread-safe parameter control
- Audio device management
- Buffer management and streaming
- Voice allocation and note tracking
- Exception handling and error recovery

Audio Processing Chain:
1. Note events → Voice allocation
2. Oscillator generation
3. ADSR envelope application
4. Filter processing
5. Voice mixing
6. Safety processing
7. Output streaming
"""

"""
Core synthesizer engine handling voice management and audio generation.

Key Functions:
- Voice allocation and stealing
- Audio buffer generation
- Real-time parameter processing
- Thread-safe state management

Classes:
    Voice: Individual voice state and processing
    Synthesizer: Main synthesis engine
"""

import numpy as np
import sounddevice as sd
import time as time_module  # Rename import to avoid conflict
from typing import Dict, Optional, List
from threading import Lock
from config import AUDIO_CONFIG, STATE
from audio import Oscillator, Filter, ADSR, dc_offset_filter, safety_limiter
from debug import DEBUG  # Add this import

class Voice:
    def __init__(self):
        self.note = 0
        self.velocity = 0
        self.active = False
        self.oscillators = [Oscillator() for _ in range(4)]
        self.filter = Filter()
        self.adsr = ADSR()

class Synthesizer:
    def __init__(self, device=None):
        self.voices: List[Voice] = [Voice() for _ in range(1)]  # Reduce to single voice
        self.stream = None
        self.lock = Lock()
        self.device = device
        self.samplerate = AUDIO_CONFIG.SAMPLE_RATE
        self.dtype = np.float32
        self.callback_mode = True  # Use callback mode instead of blocking
        
    def start(self):
        try:
            # Simple stream setup
            self.stream = sd.OutputStream(
                device=self.device,
                channels=1,
                samplerate=self.samplerate,
                blocksize=1024,  # Fixed buffer size
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()
            print("Audio stream started successfully")
            
        except Exception as e:
            DEBUG.log_error(f"Failed to start audio stream: {e}")
            raise

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            
    def note_on(self, note: int, velocity: int):
        with self.lock:
            # Find free voice or steal one
            voice = self._get_free_voice()
            if voice:
                voice.note = note
                voice.velocity = velocity / 127.0
                voice.active = True
                
    def note_off(self, note: int):
        with self.lock:
            for voice in self.voices:
                if voice.active and voice.note == note:
                    voice.active = False
                    
    def _get_free_voice(self) -> Optional[Voice]:
        # First try to find an inactive voice
        for voice in self.voices:
            if not voice.active:
                return voice
        
        # If no inactive voice, steal the oldest one
        return self.voices[0]
        
    def _prefill_buffer(self):
        dummy_buffer = np.zeros((AUDIO_CONFIG.BUFFER_SIZE * self.buffer_multiplier, 1))
        self._audio_callback(dummy_buffer, AUDIO_CONFIG.BUFFER_SIZE * self.buffer_multiplier, 0.0, None)
        
    def _on_stream_finished(self):
        if self.underflow_count > 0:
            DEBUG.log_error(f"Audio underflows occurred: {self.underflow_count}")
            
    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        try:
            # Generate simple sine wave for testing
            output = np.zeros(frames, dtype='float32')
            
            for voice in self.voices:
                if voice.active:
                    # Basic sine wave
                    frequency = 440.0 * (2.0 ** ((voice.note - 69) / 12.0))
                    t = np.linspace(0, frames / self.samplerate, frames)
                    output += np.sin(2 * np.pi * frequency * t) * voice.velocity * 0.5
            
            outdata[:] = output.reshape(-1, 1)
            
        except Exception as e:
            DEBUG.log_error(f"Audio callback error: {e}")
            outdata.fill(0)

    def _process_voice(self, voice: Voice, frames: int) -> np.ndarray:
        """Optimized voice processing"""
        voice_output = np.zeros(frames, dtype='float32')
        
        if not voice.active and voice.adsr.state == 'idle':
            return voice_output
            
        if not STATE.bypass['oscillators']:
            frequency = 440.0 * (2.0 ** ((voice.note - 69) / 12.0))
            for i, (osc, waveform) in enumerate(zip(voice.oscillators, ['sine', 'saw', 'triangle', 'pulse'])):
                if STATE.osc_mix[i] > 0.001:
                    detune_freq = frequency * (2 ** (STATE.osc_detune[i] / 12))
                    voice_output += osc.generate(detune_freq, waveform, frames) * STATE.osc_mix[i]
        
        if not STATE.bypass['adsr'] and voice.velocity > 0:
            envelope = voice.adsr.process(voice.active, STATE.adsr, frames)
            voice_output *= envelope * voice.velocity
        
        if not STATE.bypass['filter'] and (STATE.filter_cutoff < 0.99 or STATE.filter_res > 0.01):
            voice_output = voice.filter.process(voice_output, STATE.filter_cutoff, STATE.filter_res)
            
        return voice_output
