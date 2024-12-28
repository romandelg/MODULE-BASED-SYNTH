"""
Graphical User Interface
----------------------
Real-time parameter control and visualization.

Features:
1. Control Panels:
   - Oscillator mix and detune
   - Filter cutoff and resonance
   - ADSR envelope controls
   - Module bypass switches

2. Visualization:
   - Waveform display
   - Spectrum analyzer
   - Signal flow indicators
   - Performance meters

3. Real-time Updates:
   - 30 FPS refresh rate
   - Thread-safe parameter control
   - Smooth value transitions
   - Device status display
"""

import tkinter as tk
from tkinter import ttk
import numpy as np  # Fix the import statement
from threading import Thread, Lock
from typing import Dict, Any
import time
from config import STATE, AUDIO_CONFIG
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import logging

# Suppress Matplotlib debug messages
logging.getLogger('matplotlib').setLevel(logging.WARNING)

from debug import DEBUG
from lfo import LFO  # Import the LFO class

class SynthesizerGUI:
    """GUI for controlling and visualizing the synthesizer parameters"""
    
    def __init__(self, master: tk.Tk, synth):
        # Initialize all dictionaries first
        self.chain_status = {}
        self.chain_enables = {}
        self.chain_bypasses = {}
        self.signal_flow_indicators = {}
        self.signal_levels = {}
        self.master = master
        self.synth = synth  # Store the synth instance
        self.master.title("Modular Synthesizer")
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
        
        # Create main containers in correct order
        self.create_main_frame()
        self.create_oscillator_frame()
        self.create_filter_frame()
        self.create_adsr_frame()
        self.create_master_frame()
        self.create_signal_chain_frame()
        self.create_visualization_frame()
        self.create_lfo_controls()
        self.create_signal_chain_visualization()
        self.create_input_source_frame()
        self.create_sequencer_frame()
        
        self.update_interval = 1.0 / 60  # Increase to 60 FPS
        
        # Start update thread
        Thread(target=self._update_loop, daemon=True).start()

    def create_main_frame(self):
        """Create the main frame for the GUI"""
        self.main_frame = ttk.Frame(self.master)
        self.main_frame.pack(fill='both', expand=True, padx=10, pady=10)

    def create_oscillator_frame(self):
        """Create the oscillator control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Oscillators", padding=(10, 5))
        frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.osc_levels = []
        self.osc_lfo_levels = []  # Add LFO levels
        self.osc_detunes = []
        self.osc_waveforms = []
        self.osc_harmonics = []  # Add harmonics sliders
        for i in range(4):
            label = ttk.Label(frame, text=f"OSC {i+1}")
            label.grid(row=0, column=i*2, padx=2, columnspan=2)
            
            level = ttk.Progressbar(frame, orient="vertical", length=100, mode="determinate")
            level['value'] = STATE.osc_mix[i] * 100
            level.grid(row=1, column=i*2, padx=2, pady=2)
            self.osc_levels.append(level)
            
            lfo_level = ttk.Progressbar(frame, orient="vertical", length=100, mode="determinate")
            lfo_level['value'] = STATE.osc_mix[i] * 100
            lfo_level.grid(row=1, column=i*2+1, padx=2, pady=2)
            self.osc_lfo_levels.append(lfo_level)
            
            detune = ttk.Scale(frame, from_=1.0, to=-1.0, length=100, orient="vertical")
            detune.set(STATE.osc_detune[i])
            detune.grid(row=2, column=i*2, padx=2, pady=2, columnspan=2)
            detune.configure(command=lambda val, idx=i: self._update_osc_detune(val, idx))
            self.osc_detunes.append(detune)
            
            waveform = ttk.Combobox(frame, values=['sine', 'saw', 'triangle', 'pulse'])
            waveform.set(STATE.osc_waveforms[i])
            waveform.grid(row=3, column=i*2, padx=2, pady=2, columnspan=2)
            waveform.bind("<<ComboboxSelected>>", lambda event, idx=i: self._update_osc_waveform(event, idx))
            self.osc_waveforms.append(waveform)

            # Add toggle buttons for LFO mapping
            self.create_toggle_button(frame, "LFO Mix", 4, i*2, lambda idx=i: self._toggle_lfo_target(f'osc_mix_{idx}'))
            self.create_toggle_button(frame, "LFO Detune", 5, i*2, lambda idx=i: self._toggle_lfo_target(f'osc_detune_{idx}'))

            # Add harmonics slider
            ttk.Label(frame, text="Harm").grid(row=6, column=i*2, columnspan=2)
            harmonics = ttk.Scale(frame, from_=1.0, to=0.0, length=100, orient="vertical")
            harmonics.set(STATE.osc_harmonics[i])
            harmonics.grid(row=7, column=i*2, padx=2, pady=2, columnspan=2)
            harmonics.configure(command=lambda val, idx=i: self._update_osc_harmonics(val, idx))
            self.osc_harmonics.append(harmonics)

    def _update_osc_harmonics(self, value, index):
        """Update oscillator harmonics amount"""
        STATE.osc_harmonics[index] = float(value)

    def _update_osc_detune(self, value, index):
        """Update oscillator detune amount"""
        try:
            new_value = float(value)
            if STATE.osc_detune[index] != new_value:  # Only update if value changed
                STATE.osc_detune[index] = new_value
                print(f"Updated oscillator {index} detune to {value}")
        except Exception as e:
            print(f"Error updating oscillator detune: {e}")

    def _update_osc_waveform(self, event, index):
        """Update oscillator waveform"""
        waveform = event.widget.get()
        STATE.osc_waveforms[index] = waveform
        print(f"Updated oscillator {index} waveform to {waveform}")  # Debugging output

    def create_filter_frame(self):
        """Create the filter control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Filter", padding=(10, 5))
        frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Existing controls
        ttk.Label(frame, text="Cutoff").grid(row=0, column=0)
        self.cutoff = ttk.Scale(frame, from_=1.0, to=0.0, length=100, orient="vertical")
        self.cutoff.set(STATE.filter_cutoff)
        self.cutoff.grid(row=1, column=0, padx=2, pady=2)
        self.cutoff.configure(command=lambda val: self._update_filter_cutoff(val))
        
        ttk.Label(frame, text="Resonance").grid(row=0, column=1)
        self.resonance = ttk.Scale(frame, from_=1.0, to=0.0, length=100, orient="vertical")
        self.resonance.set(STATE.filter_res)
        self.resonance.grid(row=1, column=1, padx=2, pady=2)
        self.resonance.configure(command=lambda val: self._update_filter_res(val))
        
        # Add steepness control
        ttk.Label(frame, text="Steepness").grid(row=0, column=2)
        self.steepness = ttk.Scale(frame, from_=4.0, to=1.0, length=100, orient="vertical")
        self.steepness.set(STATE.filter_steepness)
        self.steepness.grid(row=1, column=2, padx=2, pady=2)
        self.steepness.configure(command=lambda val: self._update_filter_steepness(val))
        
        # Add harmonics control
        ttk.Label(frame, text="Harmonics").grid(row=0, column=3)
        self.harmonics = ttk.Scale(frame, from_=1.0, to=0.0, length=100, orient="vertical")
        self.harmonics.set(STATE.filter_harmonics)
        self.harmonics.grid(row=1, column=3, padx=2, pady=2)
        self.harmonics.configure(command=lambda val: self._update_filter_harmonics(val))
        
        ttk.Label(frame, text="Type").grid(row=0, column=4)
        self.filter_type = ttk.Combobox(frame, values=['lowpass', 'highpass', 'bandpass'])
        self.filter_type.set(STATE.filter_type)
        self.filter_type.grid(row=1, column=4, padx=2, pady=2)
        self.filter_type.bind("<<ComboboxSelected>>", self._update_filter_type)

    def _update_filter_steepness(self, value):
        """Update filter steepness"""
        STATE.filter_steepness = float(value)

    def _update_filter_harmonics(self, value):
        """Update filter harmonics"""
        STATE.filter_harmonics = float(value)

    def create_adsr_frame(self):
        """Create the ADSR envelope control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="ADSR", padding=(10, 5))
        frame.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        self.adsr_sliders = {}
        for i, param in enumerate(['attack', 'decay', 'sustain', 'release']):
            ttk.Label(frame, text=param.capitalize()).grid(row=0, column=i)
            slider = ttk.Scale(frame, from_=1.0, to=0.0, length=100, orient="vertical")
            slider.set(STATE.adsr[param])
            slider.grid(row=1, column=i, padx=2, pady=2)
            slider.configure(command=lambda val, p=param: self._update_adsr(p, val))
            self.adsr_sliders[param] = slider

    def create_visualization_frame(self):
        """Create the signal monitoring visualization frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Signal Monitoring", padding=(10, 5))
        frame.grid(row=0, column=2, rowspan=2, padx=5, pady=5, sticky="nsew")
        
        # Create waveform plot
        self.waveform_fig, self.waveform_ax = plt.subplots(figsize=(3, 1.5))
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
        self.spectrum_fig, self.spectrum_ax = plt.subplots(figsize=(3, 1.5))
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

    def _update_filter_cutoff(self, value):
        """Update filter cutoff frequency"""
        STATE.filter_cutoff = float(value)
        
    def _update_filter_res(self, value):
        """Update filter resonance"""
        STATE.filter_res = float(value)
        
    def _update_filter_type(self, event):
        """Update filter type"""
        filter_type = event.widget.get()
        STATE.filter_type = filter_type
        
    def _update_adsr(self, param, value):
        """Update ADSR envelope parameter"""
        STATE.adsr[param] = float(value)

    def _update_gain(self, value):
        """Update master gain"""
        STATE.master_gain = float(value)

    def _update_pan(self, value):
        """Update master pan"""
        STATE.master_pan = float(value)

    def _update_visualization(self):
        """Update waveform and spectrum visualization"""
        signal_data = DEBUG.get_signal_data('audio_out')
        if len(signal_data) > 0:  # Removed the zero check to always update
            self._draw_waveform(signal_data)
            self._draw_spectrum(signal_data)
            self._update_level_meter(signal_data)
        
        # Always update LFO visualization
        lfo_data = self.lfo.generate(1024)
        self._draw_lfo(lfo_data)
        
        # Force GUI elements update
        self._update_lfo_driven_elements()
        self.master.update()

    def _update_lfo_driven_elements(self):
        """Update GUI elements that are driven by the LFO"""
        for target_name, base_value in self.lfo.targets.items():
            modulated_value = getattr(STATE, target_name, base_value)
            if 'osc_mix' in target_name:
                idx = int(target_name.split('_')[-1])
                self.osc_lfo_levels[idx]['value'] = modulated_value * 100
            elif 'osc_detune' in target_name:
                idx = int(target_name.split('_')[-1])
                self.osc_detunes[idx].set(modulated_value)
            elif target_name == 'filter_cutoff':
                self.cutoff.set(modulated_value)
            elif target_name == 'filter_res':
                self.resonance.set(modulated_value)
            elif 'adsr' in target_name:
                param = target_name.split('_')[-1]
                self.adsr_sliders[param].set(modulated_value)

    def _draw_waveform(self, data):
        """Draw the waveform on the canvas"""
        if len(data) > 0:
            self.waveform_line.set_data(np.arange(len(data)), data)
            self.waveform_canvas.draw()

    def _draw_spectrum(self, data):
        """Draw the spectrum on the canvas"""
        if len(data) > 0:
            # Calculate spectrum using more bins for higher resolution
            spectrum = np.abs(np.fft.rfft(data))[:1000]  # Use more frequency bins
            
            # Apply logarithmic scaling to better show the harmonics
            spectrum = 20 * np.log10(spectrum + 1e-6)
            
            # Normalize and scale
            if np.max(spectrum) > 0:
                spectrum = (spectrum - np.min(spectrum)) / (np.max(spectrum) - np.min(spectrum)) * 100
            
            # Create logarithmic frequency axis (in Hz)
            freqs = np.logspace(1, 4, len(spectrum))  # 10 Hz to 10 kHz logarithmic scale
            
            self.spectrum_line.set_data(freqs, spectrum)
            self.spectrum_ax.set_xscale('log')  # Use logarithmic scale for x-axis
            self.spectrum_ax.set_xlim(20, 20000)  # Set frequency range from 20 Hz to 20 kHz
            self.spectrum_canvas.draw()

    def _update_level_meter(self, data):
        """Update the level meter with the peak level"""
        if len(data) > 0:
            peak_level = np.max(np.abs(data)) * 100
            self.level_meter['value'] = min(100, peak_level)

    def _draw_lfo(self, data):
        """Draw the LFO waveform on the canvas"""
        if data is not None and len(data) > 0:
            self.lfo_line.set_data(np.arange(len(data)), data)
            self.lfo_canvas.draw()

    def _update_gui_elements(self):
        """Update GUI elements to reflect current STATE values"""
        try:
            # Update oscillator controls
            for i in range(4):
                self.osc_levels[i]['value'] = STATE.osc_mix[i] * 100
                self.osc_detunes[i].set(STATE.osc_detune[i])
                self.osc_harmonics[i].set(STATE.osc_harmonics[i])
                
            # Update filter controls
            self.cutoff.set(STATE.filter_cutoff)
            self.resonance.set(STATE.filter_res)
            self.steepness.set(STATE.filter_steepness)
            self.harmonics.set(STATE.filter_harmonics)
            
            # Update ADSR
            for param, slider in self.adsr_sliders.items():
                slider.set(STATE.adsr[param])
                
            # Update master controls
            self.gain_slider.set(STATE.master_gain)
            self.pan_slider.set(STATE.master_pan)
            
            # Update LFO controls
            self.lfo_frequency.set(STATE.lfo_frequency)
            self.lfo_depth.set(STATE.lfo_depth)
            
            # Update chain status indicators only for existing modules
            for module in self.chain_status.keys():
                try:
                    self._update_chain_status(module)
                except Exception as e:
                    print(f"Error updating chain status for {module}: {e}")
            
            # Update signal flow visualization
            self._update_signal_flow()
                
        except tk.TclError as e:
            print(f"Error updating GUI elements: {e}")

    def _update_loop(self):
        """Main update loop for the GUI"""
        while self.running:
            try:
                if not self.master.winfo_exists():
                    break

                with self.update_lock:
                    # Always update visualizations
                    self._update_visualization()
                    self._update_gui_elements()
                    
                    # Update all plots
                    self.waveform_canvas.draw()
                    self.spectrum_canvas.draw()
                    self.lfo_canvas.draw()
                    
                    # Force GUI update
                    self.master.update_idletasks()
                    
            except tk.TclError as e:
                if "application has been destroyed" in str(e):
                    break
                print(f"Error: {str(e)}")
                
            time.sleep(self.update_interval)
            
    def stop(self):
        """Stop the GUI update loop"""
        self.running = False

    def update_midi_device(self, device_name: str):
        pass  # Method removed as midi_label is no longer used

    def create_toggle_button(self, frame, text, row, column, command):
        """Create a toggle button for LFO mapping"""
        button = ttk.Checkbutton(frame, text=text, command=command)
        button.grid(row=row, column=column, padx=5, pady=5)
        return button

    def _toggle_lfo_target(self, target):
        """Toggle LFO target parameter"""
        if target in self.lfo.targets:
            self.lfo.remove_target(target)
        else:
            base_value = getattr(STATE, target, 0.0)
            self.lfo.add_target(target, base_value)

    def create_master_frame(self):
        """Create the master frame containing level visualizer and controls"""
        frame = ttk.LabelFrame(self.main_frame, text="Master", padding=(10, 5))
        frame.grid(row=0, column=3, rowspan=2, padx=5, pady=5, sticky="nsew")
        
        # Level meter
        ttk.Label(frame, text="Level").grid(row=0, column=0)
        self.level_meter = ttk.Progressbar(frame, orient="vertical", length=200, mode="determinate")
        self.level_meter.grid(row=1, column=0, padx=5, pady=5)

        # Gain control
        ttk.Label(frame, text="Gain").grid(row=0, column=1)
        self.gain_slider = ttk.Scale(frame, from_=2.0, to=0.0, length=200, orient="vertical")
        self.gain_slider.set(STATE.master_gain)
        self.gain_slider.grid(row=1, column=1, padx=5, pady=5)
        self.gain_slider.configure(command=self._update_gain)

        # Pan control
        ttk.Label(frame, text="Pan").grid(row=0, column=2)
        self.pan_slider = ttk.Scale(frame, from_=1.0, to=-1.0, length=200, orient="vertical")
        self.pan_slider.set(STATE.master_pan)
        self.pan_slider.grid(row=1, column=2, padx=5, pady=5)
        self.pan_slider.configure(command=self._update_pan)

    def create_signal_chain_frame(self):
        """Create signal chain control panel with status indicators"""
        frame = ttk.LabelFrame(self.main_frame, text="Signal Chain", padding=(10, 5))
        frame.grid(row=1, column=2, padx=5, pady=5, sticky="nsew")
        
        # Header labels
        ttk.Label(frame, text="Module").grid(row=0, column=0, padx=5, sticky='w')
        ttk.Label(frame, text="Enable").grid(row=0, column=1, padx=5)
        ttk.Label(frame, text="Bypass").grid(row=0, column=2, padx=5)
        ttk.Label(frame, text="Status").grid(row=0, column=3, padx=5)
        
        # Define all modules
        modules = [
            ('Signal', 'signal'),
            ('Oscillators', 'oscillators'),
            ('Mixer', 'mixer'),
            ('Envelope', 'envelope'),
            ('Filter', 'filter'),
            ('LFO', 'lfo'),
            ('Effects', 'effects'),
            ('Amp', 'amp')
        ]
        
        # Create controls for each module
        for i, (label, key) in enumerate(modules):
            row = i + 1
            
            # Module label
            ttk.Label(frame, text=label).grid(row=row, column=0, padx=5, sticky='w')
            
            # Enable toggle
            enable_var = tk.BooleanVar(value=STATE.chain_enabled[key])
            enable = ttk.Checkbutton(frame, variable=enable_var,
                                   command=lambda k=key, v=enable_var: self._toggle_chain_enable(k, v))
            enable.grid(row=row, column=1, padx=5)
            self.chain_enables[key] = enable_var
            
            # Bypass toggle
            bypass_var = tk.BooleanVar(value=STATE.chain_bypass[key])
            bypass = ttk.Checkbutton(frame, variable=bypass_var,
                                   command=lambda k=key, v=bypass_var: self._toggle_chain_bypass(k, v))
            bypass.grid(row=row, column=2, padx=5)
            self.chain_bypasses[key] = bypass_var
            
            # Status indicator
            status = ttk.Label(frame, text="●", foreground='gray')
            status.grid(row=row, column=3, padx=5)
            self.chain_status[key] = status

    def _set_input_source(self, source):
        """Switch between MIDI and sequencer input"""
        STATE.input_source = source
        print(f"Input source changed to: {source}")
        self._update_chain_status('signal')

    def _update_chain_status(self, module):
        """Update the visual status indicator with colors"""
        try:
            if module in self.chain_status:
                if not STATE.chain_enabled[module]:
                    color = 'gray'      # Disabled
                elif STATE.chain_bypass[module]:
                    color = 'yellow'    # Bypassed
                else:
                    color = '#00ff00'   # Active (bright green)
                    
                if module == 'signal':
                    # Add input source indicator to signal module
                    source_indicator = '(M)' if STATE.input_source == 'midi' else '(S)'
                    self.chain_status[module].configure(text=f"● {source_indicator}", foreground=color)
                else:
                    self.chain_status[module].configure(text="●", foreground=color)
        except (KeyError, tk.TclError) as e:
            print(f"Error updating chain status for {module}: {e}")

    def create_lfo_controls(self):
        """Create controls for the LFO settings and routing"""
        frame = ttk.LabelFrame(self.main_frame, text="LFO", padding=(10, 5))
        frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        
        # LFO Frequency control
        ttk.Label(frame, text="Frequency").grid(row=0, column=0)
        self.lfo_frequency = ttk.Scale(frame, from_=20.0, to=0.1, length=200, orient="horizontal")
        self.lfo_frequency.set(STATE.lfo_frequency)
        self.lfo_frequency.grid(row=1, column=0, padx=5, pady=5)
        self.lfo_frequency.configure(command=self._update_lfo_frequency)
        
        # LFO Waveform selector
        ttk.Label(frame, text="Waveform").grid(row=0, column=1)
        self.lfo_waveform = ttk.Combobox(frame, values=['sine', 'triangle', 'square', 'saw'])
        self.lfo_waveform.set(STATE.lfo_waveform)
        self.lfo_waveform.grid(row=1, column=1, padx=5, pady=5)
        self.lfo_waveform.bind("<<ComboboxSelected>>", self._update_lfo_waveform)
        
        # LFO Depth control
        ttk.Label(frame, text="Depth").grid(row=0, column=2)
        self.lfo_depth = ttk.Scale(frame, from_=0.0, to=2.0, length=200, orient="horizontal")
        self.lfo_depth.set(STATE.lfo_depth)
        self.lfo_depth.grid(row=1, column=2, padx=5, pady=5)
        self.lfo_depth.configure(command=self._update_lfo_depth)
        
        # LFO Bypass button
        self.lfo_bypass_button = ttk.Button(frame, text="Bypass", command=self._toggle_lfo_bypass)
        self.lfo_bypass_button.grid(row=1, column=3, padx=5, pady=5)
        
        # Create LFO visualization
        self.lfo_fig, self.lfo_ax = plt.subplots(figsize=(3, 1))
        self.lfo_fig.patch.set_facecolor('#2e2e2e')
        self.lfo_ax.set_facecolor('#2e2e2e')
        self.lfo_canvas = FigureCanvasTkAgg(self.lfo_fig, master=frame)
        self.lfo_canvas.get_tk_widget().grid(row=2, column=0, columnspan=4, padx=5, pady=5)
        self.lfo_ax.set_title("LFO", color='white')
        self.lfo_ax.set_xlim(0, 1024)
        self.lfo_ax.set_ylim(-1, 1)
        self.lfo_ax.tick_params(axis='x', colors='white')
        self.lfo_ax.tick_params(axis='y', colors='white')
        self.lfo_line, = self.lfo_ax.plot([], [], lw=1, color='red')

    def _update_lfo_frequency(self, value):
        """Update LFO frequency"""
        self.lfo.frequency = float(value)
        STATE.lfo_frequency = float(value)

    def _update_lfo_waveform(self, event):
        """Update LFO waveform"""
        waveform = event.widget.get()
        self.lfo.waveform = waveform
        STATE.lfo_waveform = waveform

    def _update_lfo_depth(self, value):
        """Update LFO depth"""
        self.lfo.depth = float(value)
        STATE.lfo_depth = float(value)

    def _toggle_lfo_bypass(self):
        """Toggle LFO bypass state"""
        if self.lfo.bypassed:
            self.lfo.unbypass()
            self.lfo_bypass_button.configure(text="Bypass")
        else:
            self.lfo.bypass()
            self.lfo_bypass_button.configure(text="Enable")

    def create_signal_chain_visualization(self):
        """Create visual representation of the signal chain flow"""
        frame = ttk.LabelFrame(self.main_frame, text="Signal Flow", padding=(10, 5))
        frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")

        # Configure styles first
        style = ttk.Style()
        style.configure('Box.TFrame', relief='solid', borderwidth=1)
        style.configure('Active.TLabel', foreground='#00ff00')
        style.configure('Inactive.TLabel', foreground='gray')
        style.configure('Bypassed.TLabel', foreground='yellow')

        # Signal chain modules in order
        modules = [
            ('Input', 'signal'),
            ('OSC', 'oscillators'),
            ('MIX', 'mixer'),
            ('ENV', 'envelope'),
            ('FLT', 'filter'),
            ('LFO', 'lfo'),
            ('FX', 'effects'),
            ('AMP', 'amp')
        ]

        # Create the flow visualization
        for i, (label, key) in enumerate(modules):
            module_frame = ttk.Frame(frame)
            module_frame.grid(row=0, column=i*2, padx=5)

            # Module box with border
            box_frame = ttk.Frame(module_frame, style='Box.TFrame')
            box_frame.grid(row=0, column=0, pady=2)

            # Module label
            ttk.Label(box_frame, text=label).grid(row=0, column=0, padx=5, pady=2)

            # Activity indicator
            indicator = ttk.Label(box_frame, text="●", foreground='gray')
            indicator.grid(row=1, column=0, padx=5, pady=2)
            self.signal_flow_indicators[key] = indicator

            # Bypass toggle
            bypass_var = tk.BooleanVar(value=STATE.chain_bypass[key])
            ttk.Checkbutton(module_frame, text="Bypass", 
                           variable=bypass_var,
                           command=lambda k=key, v=bypass_var: self._toggle_chain_bypass(k, v)).grid(
                row=1, column=0, pady=2)

            # Draw arrow to next module (except for last module)
            if i < len(modules) - 1:
                ttk.Label(frame, text="→").grid(row=0, column=i*2 + 1)

    def _update_signal_flow(self):
        """Update signal flow visualization"""
        try:
            for module, indicator in self.signal_flow_indicators.items():
                if not STATE.chain_enabled[module]:
                    color = 'gray'  # Disabled
                    text = "●"
                elif STATE.chain_bypass[module]:
                    color = 'yellow'  # Bypassed
                    text = "○"
                else:
                    # Check if module is receiving signal
                    has_signal = self._check_module_signal(module)
                    color = '#00ff00' if has_signal else '#666666'  # Green if active with signal
                    text = "●"
                
                indicator.configure(text=text, foreground=color)
        except Exception as e:
            print(f"Error updating signal flow: {e}")

    def _check_module_signal(self, module):
        """Check if a module is receiving signal"""
        if module == 'signal':
            return STATE.input_source in ['midi', 'sequencer']
        elif module == 'oscillators':
            return any(v.active for v in self.synth.voices) if hasattr(self.synth, 'voices') else False
        elif module in ['mixer', 'envelope', 'filter', 'effects', 'amp']:
            # Check previous module in chain
            chain_order = ['signal', 'oscillators', 'mixer', 'envelope', 'filter', 'effects', 'amp']
            idx = chain_order.index(module)
            if idx > 0:
                prev_module = chain_order[idx - 1]
                return (STATE.chain_enabled[prev_module] and 
                       not STATE.chain_bypass[prev_module] and 
                       self._check_module_signal(prev_module))
        return False

    def create_input_source_frame(self):
        """Create the input source selection frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Input Source", padding=(10, 5))
        frame.grid(row=2, column=2, padx=5, pady=5, sticky="nsew")
        
        self.input_source_var = tk.StringVar(value=STATE.input_source)
        
        midi_button = ttk.Radiobutton(frame, text="MIDI", variable=self.input_source_var, value='midi', command=self._set_input_source)
        midi_button.grid(row=0, column=0, padx=5, pady=5)
        
        seq_button = ttk.Radiobutton(frame, text="Sequencer", variable=self.input_source_var, value='sequencer', command=self._set_input_source)
        seq_button.grid(row=0, column=1, padx=5, pady=5)

    def _set_input_source(self):
        """Switch between MIDI and sequencer input"""
        STATE.input_source = self.input_source_var.get()
        print(f"Input source changed to: {STATE.input_source}")
        self._update_chain_status('signal')

    def create_sequencer_frame(self):
        """Create the sequencer control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Sequencer", padding=(10, 5))
        frame.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")
        
        # Sequencer controls
        ttk.Label(frame, text="Tempo (BPM)").grid(row=0, column=0, padx=5, pady=5)
        self.tempo_slider = ttk.Scale(frame, from_=30, to=300, orient="horizontal", command=self._update_sequencer_tempo)
        self.tempo_slider.set(120)  # Default tempo
        self.tempo_slider.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(frame, text="Notes").grid(row=1, column=0, padx=5, pady=5)
        self.note_entries = []
        for i in range(8):
            entry = ttk.Entry(frame, width=5)
            entry.grid(row=1, column=i+1, padx=2, pady=2)
            self.note_entries.append(entry)
        
        self.update_notes_button = ttk.Button(frame, text="Update Notes", command=self._update_sequencer_notes)
        self.update_notes_button.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
        self.toggle_sequencer_button = ttk.Button(frame, text="Start Sequencer", command=self._toggle_sequencer)
        self.toggle_sequencer_button.grid(row=2, column=2, columnspan=2, padx=5, pady=5)

    def _update_sequencer_tempo(self, value):
        """Update sequencer tempo"""
        bpm = float(value)
        self.synth.set_sequencer_tempo(bpm)
        print(f"Sequencer tempo set to: {bpm} BPM")

    def _update_sequencer_notes(self):
        """Update sequencer notes"""
        notes = []
        for entry in self.note_entries:
            try:
                note = int(entry.get())
                notes.append(note)
            except ValueError:
                continue
        self.synth.set_sequencer_notes(notes)
        print(f"Sequencer notes updated to: {notes}")

    def _toggle_sequencer(self):
        """Toggle the sequencer on and off"""
        if STATE.sequencer_enabled:
            self.synth.toggle_sequencer(False)
            self.toggle_sequencer_button.configure(text="Start Sequencer")
        else:
            self.synth.toggle_sequencer(True)
            self.toggle_sequencer_button.configure(text="Stop Sequencer")

def create_gui(synth):
    """Create and return the main GUI window"""
    root = tk.Tk()
    gui = SynthesizerGUI(root, synth)
    return root, gui
