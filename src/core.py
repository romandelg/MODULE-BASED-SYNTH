"""
Core Synthesizer Engine
------------------------
Main audio processing system with polyphonic voice management
and real-time audio generation.
"""

import numpy as np
import sounddevice as sd
from threading import Lock
from audio import Oscillator, Filter, ADSR
from noise_sub_module import NoiseSubModule
from config import AUDIO_CONFIG, STATE
from debug import DEBUG
from lfo import LFO
import tkinter as tk
from tkinter import messagebox

class Voice:
    """Single synthesizer voice handling oscillators, envelope, filter, and noise/sub-oscillator module"""
    
    def __init__(self):
        self.note = None          # Currently playing MIDI note
        self.velocity = 0         # Note velocity (0-1)
        self.active = False       # Voice active state
        self.oscillators = [Oscillator() for _ in range(5)]  # 5 oscillators per voice
        self.adsr = ADSR()        # Amplitude envelope
        self.filter = Filter()    # Filter instance per voice
        self.noise_sub_module = NoiseSubModule()  # Noise and sub-oscillator module
        self.pre_filter_mix = np.zeros(AUDIO_CONFIG.BUFFER_SIZE)  # Signal monitoring points
        self.post_filter_mix = np.zeros(AUDIO_CONFIG.BUFFER_SIZE)
        self.sequencer_step = 0
        self.sequencer_time = 0
        self.step_duration = 44100  # One step per second by default
        self.lfo = LFO()  # Add LFO instance

    def reset(self):
        """Reset the voice to its initial state"""
        self.note = None
        self.velocity = 0
        self.active = False
        self.adsr.gate_off()

    def process(self, frames):
        """Generate audio samples for this voice"""
        if not self.active and self.adsr.state == 'idle':
            return np.zeros(frames)

        output = np.zeros(frames)
        
        # Get LFO values first
        lfo_values = self.lfo.generate(frames) * STATE.lfo_depth
        
        # Check input source before processing
        if not hasattr(STATE, 'input_source'):
            STATE.input_source = 'midi'  # Fallback to MIDI if not set

        # Update note from sequencer if enabled
        if STATE.input_source == 'sequencer' and STATE.sequencer_enabled:
            if len(STATE.sequencer_notes) == 0 or STATE.sequencer_notes[0] is None:
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

        # Calculate frequency with possible LFO pitch modulation
        if self.note is not None:
            base_freq = 440.0 * (2.0 ** ((self.note - 69) / 12.0))
            if 'pitch' in self.lfo.targets:
                pitch_mod = lfo_values * 2  # +/- 2 semitones
                frequency = base_freq * (2 ** (pitch_mod / 12))
            else:
                frequency = base_freq
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
                    # Apply LFO modulation to oscillator mix if targeted
                    mix_level = STATE.osc_mix[i]
                    if f'osc{i+1}_mix' in self.lfo.targets:
                        mix_level *= (1.0 + lfo_values)
                    output += osc_output * mix_level * self.velocity
                    DEBUG.log(f"Oscillator {i+1} output: {osc_output[:10]}")  # Log first 10 samples for debugging

        # 2. Noise and Sub-Oscillator Module
        if STATE.chain_enabled['noise_sub'] and not STATE.chain_bypass['noise_sub']:
            self.noise_sub_module.set_parameters(
                noise_amount=STATE.noise_amount,
                sub_amount=STATE.sub_amount,
                harmonics=STATE.noise_harmonics,
                inharmonicity=STATE.noise_inharmonicity
            )
            output = self.noise_sub_module.generate(output, frequency, frames)
            DEBUG.log(f"Noise/Sub-Oscillator output: {output[:10]}")  # Log first 10 samples for debugging
            
        # 3. Mixer (future mixing features)
        if STATE.chain_enabled['mixer'] and not STATE.chain_bypass['mixer']:
            output = output  # Future mixing processing
            
        # 4. Envelope
        if STATE.chain_enabled['envelope'] and not STATE.chain_bypass['envelope']:
            output = output * self.adsr.process(frames)
            DEBUG.log(f"Envelope output: {output[:10]}")  # Log first 10 samples for debugging
            
        self.pre_filter_mix = output.copy()
        
        # 5. Filter
        if STATE.chain_enabled['filter'] and not STATE.chain_bypass['filter']:
            self.filter.set_parameters(
                cutoff=STATE.filter_cutoff,
                resonance=STATE.filter_res,
                filter_type=STATE.filter_type,
                steepness=STATE.filter_steepness,
                harmonics=STATE.filter_harmonics
            )
            output = self.filter.process(output)
            DEBUG.log(f"Filter output: {output[:10]}")  # Log first 10 samples for debugging
            
        self.post_filter_mix = output.copy()
        
        # 6. Effects (future)
        if STATE.chain_enabled['effects'] and not STATE.chain_bypass['effects']:
            pass  # Future effects processing
            
        # 7. Amp
        if STATE.chain_enabled['amp'] and not STATE.chain_bypass['amp']:
            output = output  # Future amp processing
            
        # Monitor signals
        DEBUG.monitor_signal('pre_filter', self.pre_filter_mix)
        DEBUG.monitor_signal('post_filter', self.post_filter_mix)
        
        # Deactivate voice if ADSR is idle
        if self.adsr.state == 'idle':
            self.active = False

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
        self.delay_buffer = np.zeros(44100)  # 1 second max delay
        self.delay_index = 0
        self.reverb_buffer = np.zeros(44100 * 2)  # 2 seconds reverb tail
        self.reverb_index = 0

        # Initialize all mixers, filter, ADSR, and FX to zero
        self._initialize_parameters()

    def _initialize_parameters(self):
        """Initialize all mixers, filter, ADSR, and FX to zero"""
        STATE.osc_mix = [0.0] * 5
        STATE.filter_cutoff = 0.0
        STATE.filter_res = 0.0
        STATE.filter_steepness = 1.0
        STATE.adsr = {'attack': 0.5, 'decay': 0.5, 'sustain': 0.5, 'release': 0.5}  # Set ADSR to middle values
        for fx in STATE.fx_slots:
            fx['depth'] = 0.0
            fx['rate'] = 0.0
            fx['mix'] = 0.0
        print("Initialized all parameters to zero with ADSR in the middle.")

    def start(self):
        """Start the audio output stream"""
        print("Starting audio stream...")
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
            print("Audio stream started successfully")
        except Exception as e:
            print(f"Failed to start audio stream: {e}")
            DEBUG.log(f"Failed to start audio stream: {e}")
            
    def stop(self):
        """Stop the audio output stream and reset all voices"""
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.reset_all_voices()  # Ensure all voices are terminated

    def kill(self):
        """Stop all voices and restart the audio callback"""
        print("Killing all voices and restarting audio callback")
        self.stop()
        self.start()
        self._restart_oscillator_and_spectrometer()

    def _restart_oscillator_and_spectrometer(self):
        """Restart the oscillator and spectrometer"""
        for voice in self.voices:
            voice.reset()
        DEBUG.signal_monitors['audio_out'].buffer.clear()
        DEBUG.signal_monitors['pre_filter'].buffer.clear()
        DEBUG.signal_monitors['post_filter'].buffer.clear()
        print("Oscillator and spectrometer restarted.")

    def note_on(self, note: int, velocity: int):
        """Handle MIDI note on event"""
        DEBUG.log(f"Processing Note On: note={note}, velocity={velocity}")
        
        with self.lock:
            # Find free voice
            voice = self._find_free_voice()
            if voice:
                DEBUG.log(f"Assigning note {note} to voice")
                voice.note = note
                voice.velocity = velocity / 127.0
                voice.active = True
                voice.adsr.gate_on()
                DEBUG.log(f"Voice activated: note={note}, velocity={voice.velocity}")
            else:
                DEBUG.log("No free voices available!")

    def _print_recorded_sequence(self):
        """Print the recorded sequence of notes"""
        note_names = {60: 'C', 61: 'C#', 62: 'D', 63: 'D#', 64: 'E', 65: 'F', 66: 'F#', 67: 'G', 68: 'G#', 69: 'A', 70: 'A#', 71: 'B'}
        sequence = [note_names.get(note, str(note)) for note in STATE.sequencer_notes]
        print("Recorded Sequence:", " ".join(sequence))

    def _note_recorded(self):
        """Handle note recorded event"""
        if hasattr(self, 'gui'):
            self.gui._note_recorded()

    def note_off(self, note: int):
        """Handle MIDI note off event"""
        DEBUG.log(f"Processing Note Off: note={note}")
        
        with self.lock:
            for voice in self.voices:
                if voice.note == note and voice.active:
                    DEBUG.log(f"Found voice for note {note}, triggering release")
                    voice.adsr.gate_off()
                    break

    def reset_all_voices(self):
        """Reset all active voices"""
        print("Resetting all voices")  # Debugging statement
        with self.lock:
            for voice in self.voices:
                voice.reset()
            
    def _find_free_voice(self):
        """Find a free voice or steal the oldest active voice"""
        for voice in self.voices:
            if not voice.active:
                return voice
        return min(self.voices, key=lambda v: v.note if v.active else float('inf'))

    def set_sequencer_tempo(self, bpm: float):
        """Set sequencer tempo in beats per minute"""
        samples_per_beat = (60.0 / bpm) * AUDIO_CONFIG.SAMPLE_RATE
        for voice in self.voices:
            voice.step_duration = int(samples_per_beat)

    def set_sequencer_notes(self, notes: list):
        """Update the sequencer note pattern"""
        STATE.sequencer_notes = notes.copy()
        print(f"Updated sequencer pattern: {notes}")

    def process_effects(self, signal):
        """Process audio through effects chain"""
        output = signal.copy()
        
        # Process each effect slot
        for slot in STATE.fx_slots:
            if slot['type'] == 'none':
                continue
                
            effect_out = np.zeros_like(output)
            
            if slot['type'] == 'chorus':
                effect_out = self._process_chorus(output, slot)
            elif slot['type'] == 'flanger':
                effect_out = self._process_flanger(output, slot)
            elif slot['type'] == 'phaser':
                effect_out = self._process_phaser(output, slot)
            elif slot['type'] == 'reverb':
                effect_out = self._process_reverb(output, slot)
            elif slot['type'] == 'delay':
                effect_out = self._process_delay(output, slot)
            elif slot['type'] == 'distortion':
                effect_out = self._process_distortion(output, slot)
                
            # Mix dry/wet
            output = output * (1 - slot['mix']) + effect_out * slot['mix']
            
        return np.clip(output, -1.0, 1.0)

    def _process_chorus(self, signal, params):
        """Chorus effect with multiple delayed voices"""
        num_voices = 3
        output = np.zeros_like(signal)
        for i in range(num_voices):
            delay_time = 0.02 + 0.01 * np.sin(2 * np.pi * params['rate'] * np.arange(len(signal)) / AUDIO_CONFIG.SAMPLE_RATE + i * 2 * np.pi / num_voices)
            delay_samples = (delay_time * AUDIO_CONFIG.SAMPLE_RATE).astype(int)
            for j in range(len(signal)):
                idx = j - delay_samples[j]
                if idx >= 0:
                    output[j] += signal[idx] * params['depth'] / num_voices
        return output + signal

    def _process_flanger(self, signal, params):
        """Flanger effect with short delay and feedback"""
        delay_time = 0.003 + 0.002 * np.sin(2 * np.pi * params['rate'] * np.arange(len(signal)) / AUDIO_CONFIG.SAMPLE_RATE)
        delay_samples = (delay_time * AUDIO_CONFIG.SAMPLE_RATE).astype(int)
        output = np.zeros_like(signal)
        feedback = 0.7
        
        for i in range(len(signal)):
            idx = i - delay_samples[i]
            if idx >= 0:
                output[i] = signal[i] + signal[idx] * params['depth'] + output[idx] * feedback
        return output

    def _process_phaser(self, signal, params):
        """Phaser effect with all-pass filters"""
        num_stages = 6
        output = signal.copy()
        for stage in range(num_stages):
            freq = 200 + 200 * np.sin(2 * np.pi * params['rate'] * np.arange(len(signal)) / AUDIO_CONFIG.SAMPLE_RATE + stage * np.pi / num_stages)
            w0 = 2 * np.pi * freq / AUDIO_CONFIG.SAMPLE_RATE
            alpha = np.sin(w0) / 2
            a0 = 1.0 + alpha
            a1 = -2.0 * np.cos(w0)
            a2 = 1.0 - alpha
            b0 = 1.0 - alpha
            b1 = -2.0 * np.cos(w0)
            b2 = 1.0 + alpha
            
            y1, y2 = 0.0, 0.0
            x1, x2 = 0.0, 0.0
            
            for i in range(len(signal)):
                y = (b0 * output[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
                x2, x1 = x1, output[i]
                y2, y1 = y1, y
                output[i] = y
                
        return output * params['depth']

    def _process_reverb(self, signal, params):
        """Reverb effect using feedback delay network"""
        room_size = int(params['rate'] * AUDIO_CONFIG.SAMPLE_RATE)
        decay = params['depth']
        output = np.zeros_like(signal)
        
        for i in range(len(signal)):
            reverb = 0
            for offset in [room_size // 4, room_size // 2, room_size * 3 // 4]:
                idx = (self.reverb_index - offset) % len(self.reverb_buffer)
                reverb += self.reverb_buffer[idx]
            
            reverb *= decay
            output[i] = reverb
            self.reverb_buffer[self.reverb_index] = signal[i] + reverb * 0.6
            self.reverb_index = (self.reverb_index + 1) % len(self.reverb_buffer)
            
        return output

    def _process_delay(self, signal, params):
        """Delay effect with feedback"""
        delay_time = params['rate']
        feedback = params['depth']
        delay_samples = int(delay_time * AUDIO_CONFIG.SAMPLE_RATE)
        output = np.zeros_like(signal)
        
        for i in range(len(signal)):
            delay_read_idx = (self.delay_index - delay_samples + i) % len(self.delay_buffer)
            output[i] = self.delay_buffer[delay_read_idx]
            self.delay_buffer[self.delay_index] = signal[i] + output[i] * feedback
            self.delay_index = (self.delay_index + 1) % len(self.delay_buffer)
            
        return output

    def _process_distortion(self, signal, params):
        """Distortion effect with variable drive"""
        drive = 1.0 + params['depth'] * 9  # 1.0 to 10.0
        output = np.tanh(signal * drive) / np.tanh(drive)
        return output

    def _audio_callback(self, outdata, frames, time, status):
        """Audio callback for real-time audio generation"""
        if status:
            print(f"Audio callback status: {status}")
            if status.output_underflow:
                print("Output underflow detected. Restarting the stream.")
                self._show_error("Audio output underflow occurred. Restarting the audio.")
                self.kill()

        try:
            with self.lock:
                # Process LFO first
                self.lfo.generate(frames)
                
                # Update modulation targets
                self.lfo.process()  # Make sure all targets are updated
                
                output = np.zeros(frames)
                active_count = 0
                
                # Process voices with updated modulated parameters
                for voice in self.voices:
                    if voice.active:
                        voice_output = voice.process(frames)
                        if np.any(voice_output != 0):
                            active_count += 1
                            output += voice_output
                            DEBUG.log(f"Voice output: {voice_output[:10]}")  # Log first 10 samples for debugging
                
                # Apply master effects chain
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
                    
                    # Apply effects if enabled
                    if STATE.chain_enabled['effects'] and not STATE.chain_bypass['effects']:
                        output = self.process_effects(output)
                    
                    # Monitor final output
                    DEBUG.monitor_signal('audio_out', output)
                    DEBUG.log(f"Final output: {output[:10]}")  # Log first 10 samples for debugging
                    
                outdata[:] = output.reshape(outdata.shape)
                
        except ValueError as ve:
            print(f"Audio callback error (ValueError): {ve}")
            outdata.fill(0)
        except TypeError as te:
            print(f"Audio callback error (TypeError): {te}")
            outdata.fill(0)
        except IndexError as ie:
            print(f"Audio callback error (IndexError): {ie}")
            outdata.fill(0)
        except Exception as e:
            print(f"Audio callback error: {e}")
            outdata.fill(0)

    def _show_error(self, message):
        """Show an error message in a popup window"""
        root = tk.Tk()
        root.withdraw()  # Hide the root window
        messagebox.showerror("Error", message)
        root.destroy()
