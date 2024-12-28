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
        self.filter = Filter()  # Add filter instance per voice
        self.pre_filter_mix = np.zeros(AUDIO_CONFIG.BUFFER_SIZE)  # Add signal monitoring points
        self.post_filter_mix = np.zeros(AUDIO_CONFIG.BUFFER_SIZE)
        self.sequencer_step = 0
        self.sequencer_time = 0
        self.step_duration = 44100  # One step per second by default

    def reset(self):
        """Reset the voice to its initial state"""
        self.note = None
        self.velocity = 0
        self.active = False
        self.adsr.gate_off()

    def process(self, frames):
        """Generate audio samples for this voice"""
        if not self.active:
            return np.zeros(frames)

        output = np.zeros(frames)
        
        # Check input source before processing
        if not hasattr(STATE, 'input_source'):
            STATE.input_source = 'midi'  # Fallback to MIDI if not set

        # Update note from sequencer if enabled
        if STATE.input_source == 'sequencer' and STATE.sequencer_enabled:
            if len(STATE.sequencer_notes) == 0:
                return np.zeros(frames)  # Return silence if no sequencer notes are set

            self.sequencer_time += frames
            if self.sequencer_time >= self.step_duration:
                self.sequencer_time = 0
                self.sequencer_step = (self.sequencer_step + 1) % len(STATE.sequencer_notes)
                self.note = STATE.sequencer_notes[self.sequencer_step]
                self.velocity = 0.8  # Default sequencer velocity
                self.adsr.gate_on()  # Trigger new note
            elif self.sequencer_time >= self.step_duration * 0.8:  # Release note at 80% of step
                self.adsr.gate_off()

        # Calculate frequency (now supporting both MIDI and sequencer notes)
        if self.note is not None:
            frequency = 440.0 * (2.0 ** ((self.note - 69) / 12.0))
        else:
            return np.zeros(frames)

        # 1. Oscillators
        if STATE.chain_enabled['oscillators'] and not STATE.chain_bypass['oscillators']:
            for i, osc in enumerate(self.oscillators):
                if STATE.osc_mix[i] > 0.001:
                    osc_output = osc.generate(
                        frequency=frequency,
                        waveform=STATE.osc_waveforms[i],
                        samples=frames,
                        detune=STATE.osc_detune[i],
                        harmonics=STATE.osc_harmonics[i]
                    )
                    output += osc_output * STATE.osc_mix[i] * self.velocity

        # 2. Mixer (future mixing features)
        if STATE.chain_enabled['mixer'] and not STATE.chain_bypass['mixer']:
            output = output  # Future mixing processing
            
        # 3. Envelope
        if STATE.chain_enabled['envelope'] and not STATE.chain_bypass['envelope']:
            output = output * self.adsr.process(frames)
            
        self.pre_filter_mix = output.copy()
        
        # 4. Filter
        if STATE.chain_enabled['filter'] and not STATE.chain_bypass['filter']:
            self.filter.set_parameters(
                cutoff=STATE.filter_cutoff,
                resonance=STATE.filter_res,
                filter_type=STATE.filter_type,
                steepness=STATE.filter_steepness,
                harmonics=STATE.filter_harmonics
            )
            output = self.filter.process(output)
            
        self.post_filter_mix = output.copy()
        
        # 5. Effects (future)
        if STATE.chain_enabled['effects'] and not STATE.chain_bypass['effects']:
            pass  # Future effects processing
            
        # 6. Amp
        if STATE.chain_enabled['amp'] and not STATE.chain_bypass['amp']:
            output = output  # Future amp processing
            
        # Monitor signals
        DEBUG.monitor_signal('pre_filter', self.pre_filter_mix)
        DEBUG.monitor_signal('post_filter', self.post_filter_mix)
        
        return output

class Synthesizer:
    """Main synthesizer engine managing multiple voices and audio output"""
    
    def __init__(self, device=None):
        self.voices = [Voice() for _ in range(AUDIO_CONFIG.MAX_VOICES)]
        self.stream = None
        self.lock = Lock()
        self.device = device
        self.samplerate = AUDIO_CONFIG.SAMPLE_RATE
        self.lfo = LFO()  # Initialize LFO
        self.sequencer_active = False

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
                    voice.note = None  # Clear the note to stop it from sounding
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
            
    def toggle_sequencer(self, enable: bool):
        """Enable or disable the sequencer"""
        STATE.sequencer_enabled = enable
        if enable:
            print("Sequencer enabled")
            # Reset all voice sequencer positions
            for voice in self.voices:
                voice.sequencer_step = 0
                voice.sequencer_time = 0
        else:
            print("Sequencer disabled")
            # Stop all voices
            for voice in self.voices:
                voice.reset()

    def set_sequencer_tempo(self, bpm: float):
        """Set sequencer tempo in beats per minute"""
        samples_per_beat = (60.0 / bpm) * AUDIO_CONFIG.SAMPLE_RATE
        for voice in self.voices:
            voice.step_duration = int(samples_per_beat)

    def set_sequencer_notes(self, notes: list):
        """Update the sequencer note pattern"""
        STATE.sequencer_notes = notes.copy()
        print(f"Updated sequencer pattern: {notes}")

    def _audio_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """Audio callback for real-time audio generation"""
        try:
            with self.lock:
                # Handle sequencer voice allocation
                if hasattr(STATE, 'input_source') and STATE.input_source == 'sequencer':
                    if hasattr(STATE, 'sequencer_enabled') and STATE.sequencer_enabled:
                        if len(STATE.sequencer_notes) == 0:
                            outdata.fill(0)  # Return silence if no sequencer notes are set
                            return

                        if not any(v.active for v in self.voices):
                            voice = self._find_free_voice()
                            if voice:
                                voice.active = True
                                voice.note = STATE.sequencer_notes[0]
                                voice.velocity = 0.8

                # 1. Mix all active voices
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
                
                # 2. Apply LFO modulation
                self.lfo.generate(frames)
                
                # 3. Apply master effects chain
                if active_count > 0:
                    # Normalize
                    output = np.clip(output / max(1.0, active_count), -1.0, 1.0)
                    
                    # Master gain
                    output = output * STATE.master_gain
                    
                    # Master pan (if stereo)
                    if outdata.shape[1] == 2:
                        left = output * (1.0 - max(0, STATE.master_pan))
                        right = output * (1.0 + min(0, STATE.master_pan))
                        output = np.vstack((left, right)).T
                    else:
                        output = output.reshape(-1, 1)
                    
                    # Monitor final output
                    DEBUG.monitor_signal('audio_out', output)
                    
                outdata[:] = output.reshape(outdata.shape)
                
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)
