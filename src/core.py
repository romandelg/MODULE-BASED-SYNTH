"""
Core Synthesizer Engine
----------------------
Main audio processing system with polyphonic voice management
and real-time audio generation.
"""

import numpy as np
import sounddevice as sd
from threading import Lock
from audio import Oscillator, Filter, ADSR
from config import AUDIO_CONFIG, STATE
from debug import DEBUG  # Add this import
from lfo import LFO  # Import the LFO class

class Voice:
    """Single synthesizer voice handling oscillators and envelope"""
    
    def __init__(self):
        self.note = None          # Currently playing MIDI note
        self.velocity = 0         # Note velocity (0-1)
        self.active = False       # Voice active state
        self.oscillators = [Oscillator() for _ in range(4)]  # 4 oscillators per voice
        self.adsr = ADSR()       # Amplitude envelope

    def reset(self):
        """Reset the voice to its initial state"""
        self.note = None
        self.velocity = 0
        self.active = False
        self.adsr.gate_off()

    def process(self, frames):
        """Generate audio samples for this voice
        
        Returns zero buffer if voice is inactive. Otherwise, generates
        samples from all oscillators, applies ADSR envelope and 
        returns the mixed output.
        """
        if not self.active:
            return np.zeros(frames)

        # Process ADSR envelope
        adsr_output = self.adsr.process(frames)
        if self.adsr.state == 'idle':
            self.reset()
            return np.zeros(frames)

        # Calculate base frequency from MIDI note
        frequency = 440.0 * (2.0 ** ((self.note - 69) / 12.0))
        
        # Mix all oscillators
        output = np.zeros(frames)
        for i, osc in enumerate(self.oscillators):
            if STATE.osc_mix[i] > 0.001:  # Skip if oscillator is muted
                detune = STATE.osc_detune[i]
                osc_output = osc.generate(frequency, STATE.osc_waveforms[i], frames, detune)
                output += osc_output * STATE.osc_mix[i] * self.velocity
                
        return output * adsr_output  # Apply envelope

class Synthesizer:
    """Main synthesizer engine managing multiple voices and audio output"""
    
    def __init__(self, device=None):
        self.voices = [Voice() for _ in range(AUDIO_CONFIG.MAX_VOICES)]
        self.stream = None
        self.lock = Lock()
        self.device = device
        self.samplerate = AUDIO_CONFIG.SAMPLE_RATE
        self.lfo = LFO()  # Initialize LFO

    def start(self):
        """Start the audio output stream"""
        print("Starting audio stream...")
        self.stream = sd.OutputStream(
            device=self.device,
            channels=1,
            samplerate=self.samplerate,
            blocksize=AUDIO_CONFIG.BUFFER_SIZE,
            dtype='float32',
            callback=self._audio_callback
        )
        self.stream.start()
        print("Audio stream started successfully")
            
    def stop(self):
        """Stop the audio output stream"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            
    def note_on(self, note: int, velocity: int):
        """Handle MIDI note on event"""
        with self.lock:
            voice = self._find_free_voice()
            if voice:
                print(f"Note On: {note}, Velocity: {velocity}")
                voice.note = note
                voice.velocity = velocity / 127.0
                voice.active = True
                voice.adsr.set_parameters(
                    STATE.adsr['attack'],
                    STATE.adsr['decay'],
                    STATE.adsr['sustain'],
                    STATE.adsr['release']
                )
                voice.adsr.gate_on()
                
    def note_off(self, note: int):
        """Handle MIDI note off event"""
        with self.lock:
            for voice in self.voices:
                if voice.note == note:
                    print(f"Note Off: {note}")
                    voice.adsr.gate_off()  # Transition ADSR to release state
                    break

    def reset_all_voices(self):
        """Reset all active voices"""
        with self.lock:
            for voice in self.voices:
                voice.reset()
            
    def _find_free_voice(self):
        """Find a free voice or steal the oldest active voice"""
        for voice in self.voices:
            if not voice.active:
                return voice
        return min(self.voices, key=lambda v: v.note if v.active else float('inf'))
            
    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """Audio callback for real-time audio generation"""
        try:
            with self.lock:
                output = np.zeros(frames, dtype='float32')
                active_count = 0
                for voice in self.voices:
                    if voice.active:
                        try:
                            voice_output = voice.process(frames)
                            if np.any(voice_output != 0):
                                active_count += 1
                                output += voice_output
                        except Exception as ve:
                            print(f"Voice processing error: {ve}")
                
                # Apply LFO modulation
                self.lfo.generate(frames)
                
                # Normalize and apply gain/pan
                if active_count > 0:
                    output = np.clip(output / max(1.0, active_count), -1.0, 1.0)
                    output = output * STATE.master_gain  # Apply gain
                    
                    # Apply panning (if stereo output is enabled)
                    if outdata.shape[1] == 2:
                        left = output * (1.0 - max(0, STATE.master_pan))
                        right = output * (1.0 + min(0, STATE.master_pan))
                        output = np.vstack((left, right)).T
                    else:
                        output = output.reshape(-1, 1)
                    
                    DEBUG.monitor_signal('audio_out', output)
                    
                # Ensure the output array has the correct shape
                if outdata.shape != output.shape:
                    output = output.reshape(outdata.shape)
                    
                outdata[:] = output
                
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)
