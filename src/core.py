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
        """Real-time audio callback
        
        Args:
            outdata: Buffer to fill with audio samples (numpy array)
            frames: Number of frames to generate
            time_info: Timing information from audio driver
            status: Status flags from audio driver
        """
        try:
            with self.lock:
                # 1. Initialize output buffer
                output = np.zeros(frames, dtype='float32')
                
                # 2. Check if we need to generate audio
                if not self.voice.active:
                    outdata.fill(0)  # Silence if no active voice
                    return
                
                # 3. Generate audio
                frequency = 440.0 * (2.0 ** ((self.voice.note - 69) / 12.0))  # MIDI to frequency
                output = self.voice.oscillator.generate(frequency, 'sine', frames)  # Generate waveform
                output *= self.voice.velocity  # Apply velocity scaling
                
                # 4. Write to output buffer
                outdata[:] = output.reshape(-1, 1)  # Mono output
                
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)  # Safety: output silence on error
