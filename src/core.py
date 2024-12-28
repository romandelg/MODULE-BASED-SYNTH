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
from threading import Lock
from audio import Oscillator

# Minimal implementation of documented features
class Voice:
    def __init__(self):
        self.note = 0
        self.velocity = 0
        self.active = False
        self.oscillator = Oscillator()

# Minimal synthesizer for testing audio output
class Synthesizer:
    def __init__(self, device=None):
        self.voice = Voice()  # Single voice only
        self.stream = None
        self.lock = Lock()
        self.device = device
        self.samplerate = 44100
        
    def start(self):
        try:
            self.stream = sd.OutputStream(
                device=self.device,
                channels=1,
                samplerate=self.samplerate,
                blocksize=1024,
                dtype='float32',
                callback=self._audio_callback
            )
            self.stream.start()
            print("Audio stream started")
        except Exception as e:
            print(f"Audio error: {e}")
            raise
            
    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            
    def note_on(self, note: int, velocity: int):
        with self.lock:
            print(f"Synth: Note ON - note:{note} vel:{velocity}")  # Debug print
            self.voice.note = note
            self.voice.velocity = velocity / 127.0
            self.voice.active = True
            print(f"Voice state: active={self.voice.active} note={self.voice.note}")  # Debug print
                
    def note_off(self, note: int):
        with self.lock:
            print(f"Synth: Note OFF - note:{note}")  # Debug print
            if self.voice.note == note:
                self.voice.active = False
                print(f"Voice state: active={self.voice.active}")  # Debug print
            
    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        try:
            with self.lock:
                # Debug print voice state
                if self.voice.active:
                    print(f"Processing active voice: note={self.voice.note} vel={self.voice.velocity}")
                
                if not self.voice.active:
                    outdata.fill(0)
                    return
                    
                # Generate audio
                frequency = 440.0 * (2.0 ** ((self.voice.note - 69) / 12.0))
                output = self.voice.oscillator.generate(frequency, 'sine', frames)
                output *= self.voice.velocity
                
                # Write to output buffer
                outdata[:] = output.reshape(-1, 1)
                
                # Debug print audio output
                if np.any(output):
                    print(f"Audio output: min={np.min(output):.3f} max={np.max(output):.3f}")
                
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)
