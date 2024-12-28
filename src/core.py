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
from audio import Oscillator, Filter
from config import AUDIO_CONFIG, STATE
from debug import DEBUG

class Voice:
    def __init__(self):
        self.note = None
        self.velocity = 0
        self.active = False
        self.oscillators = [Oscillator() for _ in range(4)]  # Create 4 oscillators
        self.filter = Filter()

    def reset(self):
        self.note = None
        self.velocity = 0
        self.active = False

class Synthesizer:
    def __init__(self, device=None):
        self.voices = [Voice() for _ in range(AUDIO_CONFIG.MAX_VOICES)]
        self.stream = None
        self.lock = Lock()
        self.device = device
        self.samplerate = AUDIO_CONFIG.SAMPLE_RATE
        
    def start(self):
        try:
            self.stream = sd.OutputStream(
                device=self.device,
                channels=1,
                samplerate=self.samplerate,
                blocksize=AUDIO_CONFIG.BUFFER_SIZE,
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
            voice = self._find_free_voice()
            if voice:
                voice.note = note
                voice.velocity = velocity / 127.0
                voice.active = True
                print(f"Voice assigned: note={note} velocity={velocity}")
                
    def note_off(self, note: int):
        with self.lock:
            for voice in self.voices:
                if voice.note == note:
                    voice.reset()
                    print(f"Voice released: note={note}")
                    break
            
    def _find_free_voice(self):
        for voice in self.voices:
            if not voice.active:
                return voice
        # If no free voice, use voice stealing (replace the oldest active voice)
        return min(self.voices, key=lambda v: v.note if v.active else float('inf'))
            
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
                # Initialize output buffer
                output = np.zeros(frames, dtype='float32')
                
                # Mix audio from all active voices
                for voice in self.voices:
                    if voice.active:
                        frequency = 440.0 * (2.0 ** ((voice.note - 69) / 12.0))  # MIDI to frequency
                        voice.filter.cutoff = STATE.filter_cutoff
                        voice.filter.resonance = STATE.filter_res
                        voice.filter.filter_type = STATE.filter_type
                        for i, osc in enumerate(voice.oscillators):
                            if STATE.osc_mix[i] > 0.001:  # Only process if mix level is significant
                                detune = STATE.osc_detune[i]
                                osc_output = osc.generate(frequency, STATE.osc_waveforms[i], frames, detune)
                                osc_output = voice.filter.process(osc_output)
                                output += osc_output * STATE.osc_mix[i] * voice.velocity
                
                # Monitor the output signal
                DEBUG.monitor_signal('audio_out', output)
                
                # Write to output buffer
                outdata[:] = output.reshape(-1, 1)  # Mono output
                
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)  # Safety: output silence on error
