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
        style.configure('TProgressbar', background='#4e4e4e', foreground='#ffffff')
        
        # Create main containers
        self.create_main_frame()
        self.create_sequencer_frame()
        self.create_oscillator_frame()
        self.create_harmonics_frame()
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

    def create_main_frame(self):
        """Create the main frame for the GUI"""
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)

    def create_sequencer_frame(self):
        """Create the sequencer control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Sequencer", padding=(10, 5))
        frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        # Add sequencer controls here

    def create_oscillator_frame(self):
        """Create the oscillator control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Oscillator", padding=(10, 5))
        frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
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

    def create_harmonics_frame(self):
        """Create the harmonics control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Harmonics", padding=(10, 5))
        frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        # Add harmonics controls here

    def create_adsr_frame(self):
        """Create the ADSR envelope control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="ADSR Envelope", padding=(10, 5))
        frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        # ADSR sliders
        adsr_params = {
            'Attack': (0.0, 2.0, STATE.adsr['attack']),
            'Decay': (0.0, 2.0, STATE.adsr['decay']),
            'Sustain': (0.0, 1.0, STATE.adsr['sustain']),
            'Release': (0.0, 3.0, STATE.adsr['release'])
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
        # Add filter controls here

    def create_lfo_frame(self):
        """Create the LFO control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="LFO", padding=(10, 5))
        frame.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        # Add LFO controls here

    def create_effects_frame(self):
        """Create the effects control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Effects", padding=(10, 5))
        frame.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")
        # Add effects controls here

    def create_amp_frame(self):
        """Create the amp control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Amp", padding=(10, 5))
        frame.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")
        # Add amp controls here

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
        # Add bypass controls here

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
        self.spectrum_canvas.get_tk_widget().grid(row=1, column=0, padx=5, pady=5)
        self.spectrum_ax.set_title("Spectrum", color='white')
        self.spectrum_ax.set_xlim(0, 200)  # Limit to first 200 frequency bins
        self.spectrum_ax.set_ylim(0, 100)
        self.spectrum_ax.tick_params(axis='x', colors='white')
        self.spectrum_ax.tick_params(axis='y', colors='white')
        self.spectrum_line, = self.spectrum_ax.plot([], [], lw=1, color='red')

    def _update_loop(self):
        """Main update loop for the GUI"""
        while self.running:
            try:
                if not self.master.winfo_exists():
                    break

                with self.update_lock:
                    # Update visualizations
                    self._update_visualization()
                    self._update_lfo_leds()
                    
                    # Force GUI update
                    self.master.update_idletasks()
                    
            except tk.TclError as e:
                if "application has been destroyed" in str(e):
                    break
                print(f"Error: {str(e)}")
                
            time.sleep(self.update_interval)
            
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
            spectrum = np.abs(np.fft.rfft(data))[:1000]  # Use more frequency bins
            spectrum = 20 * np.log10(spectrum + 1e-6)  # Apply logarithmic scaling
            if np.max(spectrum) > 0:
                spectrum = (spectrum - np.min(spectrum)) / (np.max(spectrum) - np.min(spectrum)) * 100
            freqs = np.logspace(1, 4, len(spectrum))  # 10 Hz to 10 kHz logarithmic scale
            self.spectrum_line.set_data(freqs, spectrum)
            self.spectrum_ax.set_xscale('log')  # Use logarithmic scale for x-axis
            self.spectrum_ax.set_xlim(20, 20000)  # Set frequency range from 20 Hz to 20 kHz
            self.spectrum_canvas.draw()

    def stop(self):
        """Stop the GUI update loop"""
        self.running = False

def create_gui_v2(synth):
    """Create and return the main GUI window"""
    root = tk.Tk()
    gui = SynthesizerGUIV2(root, synth)
    return root, gui
