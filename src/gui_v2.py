"""
Graphical User Interface v2
---------------------------
Real-time parameter control and visualization with enhanced modularity.

Features:
1. Control Panels:
   - Sequencer
   - Oscillator
   - Harmonics
   - ADSR Envelope
   - Filter
   - LFO
   - Effects
   - Amp
   - Post-Oscillator (Noise, Sub-Oscillator, Harmonics, Inharmonicity)

2. Bypass Functionality:
   - Module toggles for enabling/disabling and bypassing

3. Visualization:
   - Waveform display
   - Spectrum analyzer

4. Real-time Updates:
   - 60 FPS refresh rate
   - Thread-safe parameter control
   - Smooth value transitions
   - Device status display
"""

import tkinter as tk
from tkinter import ttk
import numpy as np
from threading import Thread, Lock
import time
from config import STATE, AUDIO_CONFIG
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import logging

# Suppress Matplotlib debug messages
logging.getLogger('matplotlib').setLevel(logging.WARNING)

from debug import DEBUG
from lfo import LFO

class SynthesizerGUIV2:
    """GUI for controlling and visualizing the synthesizer parameters"""
    
    def __init__(self, master: tk.Tk, synth):
        self.master = master
        self.synth = synth
        self.master.title("Modular Synthesizer v2")
        self.master.configure(bg='#2e2e2e')
        self.update_lock = Lock()
        self.running = True
        
        # Handle window close event
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Initialize LFO
        self.lfo = LFO()
        
        # Apply dark mode style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#2e2e2e')
        style.configure('TLabel', background='#2e2e2e', foreground='#ffffff')
        style.configure('TButton', background='#4e4e4e', foreground='#ffffff')
        style.configure('TCombobox', fieldbackground='#4e4e4e', background='#4e4e4e', foreground='#ffffff')
        style.configure('TScale', background='#2e2e2e', foreground='#ffffff')
        style.configure('TProgressbar', background='#4e4e2e', foreground='#ffffff')
        
        # Create main containers
        self.create_main_frame()
        self.create_sequencer_frame()
        self.create_oscillator_frame()
        self.create_adsr_frame()
        self.create_filter_frame()
        self.create_lfo_frame()
        self.create_effects_frame()
        self.create_amp_frame()
        self.create_post_oscillator_frame()
        self.create_bypass_frame()
        self.create_visualization_frame()
        
        self.update_interval = 1.0 / 60  # 60 FPS
        
        # Start update thread
        Thread(target=self._update_loop, daemon=True).start()

        # Add Kill button
        kill_button = tk.Button(self.master, text="Kill", command=self.synth.kill)
        kill_button.pack(pady=10)

        # Add Close button
        close_button = tk.Button(self.master, text="Close", command=self.master.quit)
        close_button.pack(pady=10)

    def create_main_frame(self):
        """Create the main frame for the GUI"""
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)

    def create_sequencer_frame(self):
        """Create the sequencer control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Sequencer", padding=(10, 5))
        frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Remove Enable/Disable toggle (Play)
        # ttk.Checkbutton(frame, text="Enable Sequencer", 
        #                command=lambda: self.synth.toggle_sequencer(STATE.sequencer_enabled)).grid(row=0, column=0)
        
        # Record button
        rec_button = ttk.Button(frame, text="Rec", command=self._start_record)
        rec_button.grid(row=0, column=0, padx=5)
        
        # Play/Pause button
        play_pause_button = ttk.Button(frame, text="Play/Pause", command=self._toggle_play_pause)
        play_pause_button.grid(row=0, column=1, padx=5)

        # BPM control
        ttk.Label(frame, text="BPM").grid(row=1, column=0)
        bpm_slider = ttk.Scale(frame, from_=60, to=200, orient='horizontal')
        bpm_slider.set(120)
        bpm_slider.grid(row=1, column=1)
        bpm_slider.configure(command=lambda v: self.synth.set_sequencer_tempo(float(v)))

        # Remove octave shift control
        # ttk.Label(frame, text="Octave Shift").grid(row=2, column=0)
        # octave_shift = ttk.Scale(frame, from_=-2, to=2, orient='horizontal')
        # octave_shift.set(STATE.sequencer_octave_shift)
        # octave_shift.grid(row=2, column=1)
        # octave_shift.configure(command=lambda v: setattr(STATE, 'sequencer_octave_shift', int(v)))

        # Recording LED
        self.record_led = tk.Canvas(frame, width=20, height=20, bg="gray20", highlightthickness=0)
        self.record_led.create_oval(5, 5, 15, 15, fill="gray")
        self.record_led.grid(row=0, column=2, padx=5)

        # Recorded sequence label
        self.sequence_label = ttk.Label(frame, text="Sequence: ")
        self.sequence_label.grid(row=3, column=0, columnspan=3, padx=5, pady=5)

        # Toggle switch for real-time/live notes or sequencer
        self.play_mode = tk.StringVar(value="live")
        ttk.Radiobutton(frame, text="Live", variable=self.play_mode, value="live", command=self._update_play_mode).grid(row=4, column=0, padx=5, pady=5)
        ttk.Radiobutton(frame, text="Sequencer", variable=self.play_mode, value="sequencer", command=self._update_play_mode).grid(row=4, column=1, padx=5, pady=5)

    def _update_play_mode(self):
        """Update the play mode based on the toggle switch"""
        STATE.input_source = self.play_mode.get()
        if STATE.input_source == 'sequencer':
            self.synth.toggle_sequencer(True)  # Enable sequencer when switched to sequencer mode
        else:
            self.synth.toggle_sequencer(False)  # Disable sequencer when switched to live mode
        print(f"Play mode set to: {STATE.input_source}")

    def _start_record(self):
        """Toggle recording state for the sequencer"""
        if STATE.sequencer_recording:
            # Stop recording
            STATE.sequencer_recording = False
            self._update_record_led()
            self._update_sequence_label()
            print("Sequencer recording stopped.")
        else:
            # Start recording
            STATE.sequencer_recording = True
            STATE.sequencer_record_count = 0
            STATE.sequencer_notes = []
            self._update_record_led()
            print("Recording notes...")

    def _toggle_play_pause(self):
        """Toggle play/pause for the sequencer"""
        STATE.sequencer_enabled = not STATE.sequencer_enabled
        if STATE.sequencer_enabled:
            print("Sequencer playing...")
        else:
            print("Sequencer paused...")

    def _update_record_led(self):
        """Update the recording LED based on the recording state"""
        if STATE.sequencer_recording:
            self.record_led.itemconfig(1, fill="red")
        else:
            self.record_led.itemconfig(1, fill="gray")

    def _note_recorded(self):
        """Handle note recorded event"""
        self._update_record_led()
        self._update_sequence_label()
        print("Note recorded.")

    def _update_sequence_label(self):
        """Update the sequence label with the recorded notes"""
        note_names = {60: 'C', 61: 'C#', 62: 'D', 63: 'D#', 64: 'E', 65: 'F', 66: 'F#', 67: 'G', 68: 'G#', 69: 'A', 70: 'A#', 71: 'B'}
        sequence = [note_names.get(note, str(note)) for note in STATE.sequencer_notes]
        self.sequence_label.config(text="Sequence: " + " ".join(sequence))

    def create_oscillator_frame(self):
        """Create the oscillator control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Oscillator", padding=(10, 5))
        frame.grid(row=0, column=1, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        self.osc_mix_levels = []
        self.osc_detunes = []
        self.osc_lfo_leds = []

        waveforms = ['sine', 'saw', 'triangle', 'pulse', 'noise']
        for i in range(5):
            ttk.Label(frame, text=f"OSC {i+1} ({waveforms[i]})").grid(row=i, column=0, padx=5, pady=5)
            
            # Mix level
            mix_level = ttk.Scale(frame, from_=0.0, to=1.0, length=100, orient="horizontal")
            mix_level.set(STATE.osc_mix[i])
            mix_level.grid(row=i, column=1, padx=5, pady=5)
            mix_level.configure(command=lambda val, idx=i: self._update_osc_mix(val, idx))
            self.osc_mix_levels.append(mix_level)
            
            # Detune level
            detune = ttk.Scale(frame, from_=-1.0, to=1.0, length=100, orient="horizontal")
            detune.set(STATE.osc_detune[i])
            detune.grid(row=i, column=2, padx=5, pady=5)
            detune.configure(command=lambda val, idx=i: self._update_osc_detune(val, idx))
            self.osc_detunes.append(detune)
            
            # LFO trigger with LED simulation
            lfo_button = ttk.Checkbutton(frame, text="LFO", command=lambda idx=i: self._toggle_lfo_target(f'osc_mix_{idx}'))
            lfo_button.grid(row=i, column=3, padx=5, pady=5)
            
            led = tk.Canvas(frame, width=20, height=20, bg="gray20", highlightthickness=0)
            led.create_oval(5, 5, 15, 15, fill="gray")
            led.grid(row=i, column=4, padx=5, pady=5)
            self.osc_lfo_leds.append(led)

    def _update_osc_mix(self, value, index):
        """Update oscillator mix level"""
        STATE.osc_mix[index] = float(value)

    def _update_osc_detune(self, value, index):
        """Update oscillator detune level"""
        STATE.osc_detune[index] = float(value)

    def _toggle_lfo_target(self, target):
        """Toggle LFO target parameter"""
        if target in self.lfo.targets:
            self.lfo.remove_target(target)
        else:
            base_value = getattr(STATE, target, 0.0)
            self.lfo.add_target(target, base_value)

    def _update_lfo_leds(self):
        """Update the brightness of the LFO LEDs based on modulation"""
        for idx, led in enumerate(self.osc_lfo_leds):
            if f'osc_mix_{idx}' in self.lfo.targets:
                brightness = int(255 * abs(self.lfo.targets[f'osc_mix_{idx}']))
                color = f'#{brightness:02x}{brightness:02x}{brightness:02x}'
                led.itemconfig(1, fill=color)
            else:
                led.itemconfig(1, fill="gray")

    def create_adsr_frame(self):
        """Create the ADSR envelope control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="ADSR Envelope", padding=(10, 5))
        frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # ADSR sliders
        adsr_params = {
            'Attack': (0.0, 2.0, STATE.adsr['attack']),
            'Decay': (0.0, 2.0, STATE.adsr['decay']),
            'Sustain': (0.0, 1.0, STATE.adsr['sustain']),
            'Release': (0.0, 1.0, STATE.adsr['release'])  # Maximum 1 second
        }
        
        for i, (param, (min_val, max_val, default)) in enumerate(adsr_params.items()):
            ttk.Label(frame, text=param).grid(row=i, column=0, padx=5)
            slider = ttk.Scale(
                frame,
                from_=min_val,
                to=max_val,
                value=default,
                orient='horizontal',
                length=200
            )
            slider.grid(row=i, column=1, padx=5, pady=2)
            
            # Update function for each parameter
            def update_adsr(value, param=param.lower()):
                STATE.adsr[param] = float(value)
            
            slider.configure(command=lambda v, p=param.lower(): update_adsr(v, p))

    def create_filter_frame(self):
        """Create the filter control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Filter", padding=(10, 5))
        frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        
        # Cutoff control with logarithmic scaling
        ttk.Label(frame, text="Cutoff").grid(row=0, column=0)
        cutoff = ttk.Scale(
            frame,
            from_=20,     # Minimum frequency
            to=20000,     # Maximum frequency
            orient='horizontal',
            length=200
        )
        cutoff.set(STATE.filter_cutoff)
        cutoff.grid(row=0, column=1)
        
        def update_cutoff(value):
            # Convert linear slider value to logarithmic frequency
            freq = float(value)
            # Normalize frequency to 0-1 range for the filter
            normalized = (np.log10(freq) - np.log10(20)) / (np.log10(20000) - np.log10(20))
            STATE.filter_cutoff = normalized
            
        cutoff.configure(command=update_cutoff)
        
        # Resonance control
        ttk.Label(frame, text="Resonance").grid(row=1, column=0)
        resonance = ttk.Scale(frame, from_=0, to=1, orient='horizontal')
        resonance.set(STATE.filter_res)
        resonance.grid(row=1, column=1)
        resonance.configure(command=lambda v: setattr(STATE, 'filter_res', float(v)))
        
        # Steepness control (new)
        ttk.Label(frame, text="Steepness").grid(row=2, column=0)
        steepness = ttk.Scale(frame, from_=1, to=4, orient='horizontal')
        steepness.set(STATE.filter_steepness)
        steepness.grid(row=2, column=1)
        steepness.configure(command=lambda v: setattr(STATE, 'filter_steepness', float(v)))
        
        # Filter type selector
        ttk.Label(frame, text="Type").grid(row=3, column=0)
        filter_type = ttk.Combobox(frame, values=['lowpass', 'highpass', 'bandpass'])
        filter_type.set(STATE.filter_type)
        filter_type.grid(row=3, column=1)
        filter_type.bind('<<ComboboxSelected>>', lambda e: setattr(STATE, 'filter_type', filter_type.get()))

    def create_lfo_frame(self):
        """Create the LFO control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="LFO", padding=(10, 5))
        frame.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        
        # Frequency control (previously rate)
        ttk.Label(frame, text="Frequency").grid(row=0, column=0)
        frequency = ttk.Scale(frame, from_=0.1, to=20, orient='horizontal')
        frequency.set(self.lfo.frequency)
        frequency.grid(row=0, column=1)
        frequency.configure(command=lambda v: setattr(self.lfo, 'frequency', float(v)))
        
        # Depth control
        ttk.Label(frame, text="Depth").grid(row=1, column=0)
        depth = ttk.Scale(frame, from_=0, to=1, orient='horizontal')
        depth.set(self.lfo.depth)
        depth.grid(row=1, column=1)
        depth.configure(command=lambda v: setattr(self.lfo, 'depth', float(v)))
        
        # Waveform selector
        ttk.Label(frame, text="Waveform").grid(row=2, column=0)
        waveform = ttk.Combobox(frame, values=['sine', 'triangle', 'square', 'saw'])
        waveform.set(self.lfo.waveform)
        waveform.grid(row=2, column=1)
        waveform.bind('<<ComboboxSelected>>', lambda e: setattr(self.lfo, 'waveform', waveform.get()))

    def create_effects_frame(self):
        """Create the effects control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Effects", padding=(10, 5))
        frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        
        # Create effect slots
        for slot in range(3):
            slot_frame = ttk.LabelFrame(frame, text=f"Effect {slot + 1}", padding=(5, 5))
            slot_frame.grid(row=slot, column=0, padx=5, pady=5, sticky="ew")
            
            # Effect type selector
            fx_type = ttk.Combobox(slot_frame, values=STATE.available_fx)
            fx_type.set(STATE.fx_slots[slot]['type'])
            fx_type.grid(row=0, column=0, padx=5, pady=2)
            fx_type.bind('<<ComboboxSelected>>', 
                        lambda e, s=slot: self._update_fx_param(s, 'type', e.widget.get()))
            
            # Depth control
            ttk.Label(slot_frame, text="Depth").grid(row=0, column=1)
            depth = ttk.Scale(slot_frame, from_=0, to=1, orient='horizontal')
            depth.set(STATE.fx_slots[slot]['depth'])
            depth.grid(row=0, column=2, padx=5, pady=2)
            depth.configure(command=lambda v, s=slot: self._update_fx_param(s, 'depth', float(v)))
            
            # Rate control
            ttk.Label(slot_frame, text="Rate").grid(row=0, column=3)
            rate = ttk.Scale(slot_frame, from_=0.1, to=10, orient='horizontal')
            rate.set(STATE.fx_slots[slot]['rate'])
            rate.grid(row=0, column=4, padx=5, pady=2)
            rate.configure(command=lambda v, s=slot: self._update_fx_param(s, 'rate', float(v)))
            
            # Mix control
            ttk.Label(slot_frame, text="Mix").grid(row=0, column=5)
            mix = ttk.Scale(slot_frame, from_=0, to=1, orient='horizontal')
            mix.set(STATE.fx_slots[slot]['mix'])
            mix.grid(row=0, column=6, padx=5, pady=2)
            mix.configure(command=lambda v, s=slot: self._update_fx_param(s, 'mix', float(v)))

    def _update_fx_param(self, slot, param, value):
        """Update effect parameter for a specific slot"""
        STATE.fx_slots[slot][param] = value
        STATE.chain_enabled['effects'] = True
        STATE.chain_bypass['effects'] = False

    def create_amp_frame(self):
        """Create the amp control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Amp", padding=(10, 5))
        frame.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
        
        # Master volume
        ttk.Label(frame, text="Master").grid(row=0, column=0)
        master = ttk.Scale(frame, from_=0, to=1, orient='horizontal')
        master.set(STATE.master_gain)
        master.grid(row=0, column=1)
        master.configure(command=lambda v: setattr(STATE, 'master_gain', float(v)))
        
        # Pan control
        ttk.Label(frame, text="Pan").grid(row=1, column=0)
        pan = ttk.Scale(frame, from_=-1, to=1, orient='horizontal')
        pan.set(STATE.master_pan)
        pan.grid(row=1, column=1)
        pan.configure(command=lambda v: setattr(STATE, 'master_pan', float(v)))

    def create_post_oscillator_frame(self):
        """Create the post-oscillator control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Post-Oscillator", padding=(10, 5))
        frame.grid(row=2, column=2, padx=5, pady=5, sticky="nsew")
        
        # Removed "Noise Amount" label and scale
        
        # Sub-oscillator amount
        ttk.Label(frame, text="Sub Amount").grid(row=0, column=1, padx=5, pady=5)
        sub_amount = ttk.Scale(frame, from_=0.0, to=1.0, length=100, orient="horizontal")
        sub_amount.set(STATE.sub_amount)
        sub_amount.grid(row=1, column=1, padx=5, pady=5)
        sub_amount.configure(command=lambda val: self._update_sub_amount(val))
        
        # Harmonics
        ttk.Label(frame, text="Harmonics").grid(row=0, column=2, padx=5, pady=5)
        noise_harmonics = ttk.Scale(frame, from_=0.0, to=1.0, length=100, orient="horizontal")
        noise_harmonics.set(STATE.noise_harmonics)
        noise_harmonics.grid(row=1, column=2, padx=5, pady=5)
        noise_harmonics.configure(command=lambda val: self._update_noise_harmonics(val))
        
        # Inharmonicity
        ttk.Label(frame, text="Inharmonicity").grid(row=0, column=3, padx=5, pady=5)
        noise_inharmonicity = ttk.Scale(frame, from_=0.0, to=1.0, length=100, orient="horizontal")
        noise_inharmonicity.set(STATE.noise_inharmonicity)
        noise_inharmonicity.grid(row=1, column=3, padx=5, pady=5)
        noise_inharmonicity.configure(command=lambda val: self._update_noise_inharmonicity(val))

    def _update_noise_amount(self, value):
        # Removed or commented out since it's no longer used
        pass

    def _update_sub_amount(self, value):
        """Update sub-oscillator amount"""
        STATE.sub_amount = float(value)

    def _update_noise_harmonics(self, value):
        """Update noise harmonics"""
        STATE.noise_harmonics = float(value)

    def _update_noise_inharmonicity(self, value):
        """Update noise inharmonicity"""
        STATE.noise_inharmonicity = float(value)

    def create_bypass_frame(self):
        """Create the bypass control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Bypass Controls", padding=(10, 5))
        frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        
        modules = ['oscillators', 'noise_sub', 'mixer', 'envelope', 'filter', 'effects', 'amp']
        for i, module in enumerate(modules):
            ttk.Checkbutton(frame, text=f"{module.title()}", 
                          command=lambda m=module: self._toggle_bypass(m)).grid(row=0, column=i, padx=5)

    def _toggle_bypass(self, module):
        """Toggle bypass state for a module"""
        STATE.chain_bypass[module] = not STATE.chain_bypass[module]

    def create_visualization_frame(self):
        """Create the visualization frame for waveform and spectrum"""
        frame = ttk.LabelFrame(self.main_frame, text="Visualization", padding=(10, 5))
        frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        
        # Create waveform plot
        self.waveform_fig, self.waveform_ax = plt.subplots(figsize=(5, 2))
        self.waveform_fig.patch.set_facecolor('#2e2e2e')
        self.waveform_ax.set_facecolor('#2e2e2e')
        self.waveform_canvas = FigureCanvasTkAgg(self.waveform_fig, master=frame)
        self.waveform_canvas.get_tk_widget().grid(row=0, column=0, padx=5, pady=5)
        self.waveform_ax.set_title("Waveform", color='white')
        self.waveform_ax.set_xlim(0, 1024)
        self.waveform_ax.set_ylim(-1, 1)
        self.waveform_ax.tick_params(axis='x', colors='white')
        self.waveform_ax.tick_params(axis='y', colors='white')
        self.waveform_line, = self.waveform_ax.plot([], [], lw=1, color='red')
        
        # Create spectrum plot
        self.spectrum_fig, self.spectrum_ax = plt.subplots(figsize=(5, 2))
        self.spectrum_fig.patch.set_facecolor('#2e2e2e')
        self.spectrum_ax.set_facecolor('#2e2e2e')
        self.spectrum_canvas = FigureCanvasTkAgg(self.spectrum_fig, master=frame)
        self.spectrum_canvas.get_tk_widget().grid(row=0, column=1, padx=5, pady=5)
        self.spectrum_ax.set_title("Spectrum", color='white')
        self.spectrum_ax.set_xlim(20, 20000)  # Set frequency range from 20 Hz to 20 kHz
        self.spectrum_ax.set_ylim(-100, 100)  # Set dB range from -100 to +100
        self.spectrum_ax.set_xscale('log')  # Use logarithmic scale for x-axis
        self.spectrum_ax.tick_params(axis='x', colors='white')
        self.spectrum_ax.tick_params(axis='y', colors='white')
        self.spectrum_line, = self.spectrum_ax.plot([], [], lw=1, color='red')

    def _update_visualization(self):
        """Update waveform and spectrum visualization"""
        signal_data = DEBUG.get_signal_data('audio_out')
        if len(signal_data) > 0:
            self._draw_waveform(signal_data)
            self._draw_spectrum(signal_data)
        
        # Force GUI elements update
        self.master.update()

    def _draw_waveform(self, data):
        """Draw the waveform on the canvas"""
        if len(data) > 0:
            self.waveform_line.set_data(np.arange(len(data)), data)
            self.waveform_canvas.draw()

    def _draw_spectrum(self, data):
        """Draw the spectrum on the canvas"""
        if len(data) > 0:
            spectrum = np.abs(np.fft.rfft(data))  # Use more frequency bins
            spectrum = 20 * np.log10(spectrum + 1e-6)  # Apply logarithmic scaling
            freqs = np.fft.rfftfreq(len(data), 1 / AUDIO_CONFIG.SAMPLE_RATE)
            self.spectrum_line.set_data(freqs, spectrum)
            self.spectrum_canvas.draw()

    def stop(self):
        """Stop the GUI update loop"""
        self.running = False

    def on_close(self):
        """Handle the GUI window close event"""
        self.running = False
        self.master.destroy()
        self.synth.stop()
        print("GUI closed and script stopped.")

    def _update_loop(self):
        """Periodic update loop for the GUI"""
        while self.running:
            with self.update_lock:
                self._update_visualization()
            time.sleep(self.update_interval)

def create_gui_v2(synth):
    """Create and return the main GUI window"""
    root = tk.Tk()
    gui = SynthesizerGUIV2(root, synth)
    return root, gui
