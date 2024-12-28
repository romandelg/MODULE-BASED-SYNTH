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

class SynthesizerGUI:
    """GUI for controlling and visualizing the synthesizer parameters"""
    
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Modular Synthesizer")
        self.master.configure(bg='#2e2e2e')
        self.update_lock = Lock()
        self.running = True
        
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
        self.create_oscillator_frame()
        self.create_filter_frame()
        self.create_adsr_frame()
        self.create_visualization_frame()
        self.create_level_visualizer()
        self.create_kill_audio_button()  # Add Kill Audio button
        
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
        self.osc_detunes = []
        self.osc_waveforms = []
        for i in range(4):
            label = ttk.Label(frame, text=f"OSC {i+1}")
            label.grid(row=0, column=i, padx=2)
            
            level = ttk.Progressbar(frame, orient="vertical", length=100, mode="determinate")
            level['value'] = STATE.osc_mix[i] * 100
            level.grid(row=1, column=i, padx=2, pady=2)
            self.osc_levels.append(level)
            
            detune = ttk.Scale(frame, from_=1.0, to=-1.0, length=100, orient="vertical")
            detune.set(STATE.osc_detune[i])
            detune.grid(row=2, column=i, padx=2, pady=2)
            detune.configure(command=lambda val, idx=i: self._update_osc_detune(val, idx))
            self.osc_detunes.append(detune)
            
            waveform = ttk.Combobox(frame, values=['sine', 'saw', 'triangle', 'pulse'])
            waveform.set(STATE.osc_waveforms[i])
            waveform.grid(row=3, column=i, padx=2, pady=2)
            waveform.bind("<<ComboboxSelected>>", lambda event, idx=i: self._update_osc_waveform(event, idx))
            self.osc_waveforms.append(waveform)
            
    def create_filter_frame(self):
        """Create the filter control frame"""
        frame = ttk.LabelFrame(self.main_frame, text="Filter", padding=(10, 5))
        frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
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
        
        ttk.Label(frame, text="Type").grid(row=0, column=2)
        self.filter_type = ttk.Combobox(frame, values=['lowpass', 'highpass', 'bandpass'])
        self.filter_type.set(STATE.filter_type)
        self.filter_type.grid(row=1, column=2, padx=2, pady=2)
        self.filter_type.bind("<<ComboboxSelected>>", self._update_filter_type)
        
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
        self.spectrum_ax.set_xlim(0, 512)
        self.spectrum_ax.set_ylim(0, 200)  # Update y-axis limit to 200
        self.spectrum_ax.tick_params(axis='x', colors='white')
        self.spectrum_ax.tick_params(axis='y', colors='white')
        self.spectrum_line, = self.spectrum_ax.plot([], [], lw=1, color='red')

    def create_level_visualizer(self):
        """Create the master level, gain, and pan controls"""
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

    def create_kill_audio_button(self):
        """Create the Kill Audio button to stop all active notes"""
        button = ttk.Button(self.main_frame, text="Kill Audio", command=self._kill_audio)
        button.grid(row=2, column=3, padx=5, pady=5, sticky="nsew")

    def _kill_audio(self):
        """Stop all active notes"""
        for voice in self.master.voices:
            voice.reset()

    def _update_osc_mix(self, value, index):
        """Update oscillator mix level"""
        STATE.osc_mix[index] = float(value)
        self.osc_levels[index]['value'] = float(value) * 100
        
    def _update_osc_detune(self, value, index):
        """Update oscillator detune amount"""
        STATE.osc_detune[index] = float(value)
        
    def _update_osc_waveform(self, event, index):
        """Update oscillator waveform"""
        waveform = event.widget.get()
        STATE.osc_waveforms[index] = waveform
        
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
        if len(signal_data) > 0 and not np.all(signal_data == 0):
            self._draw_waveform(signal_data)
            self._draw_spectrum(signal_data)
            self._update_level_meter(signal_data)

    def _draw_waveform(self, data):
        """Draw the waveform on the canvas"""
        if len(data) > 0:
            self.waveform_line.set_data(np.arange(len(data)), data)
            self.waveform_canvas.draw()

    def _draw_spectrum(self, data):
        """Draw the spectrum on the canvas"""
        if len(data) > 0:
            spectrum = np.abs(np.fft.fft(data))[:len(data)//2]
            if np.max(spectrum) > 0:
                spectrum = spectrum / np.max(spectrum) * 200
            self.spectrum_line.set_data(np.arange(len(spectrum)), spectrum)
            self.spectrum_canvas.draw()

    def _update_level_meter(self, data):
        """Update the level meter with the peak level"""
        if len(data) > 0:
            peak_level = np.max(np.abs(data)) * 100
            self.level_meter['value'] = min(100, peak_level)

    def _update_gui_elements(self):
        """Update GUI elements to reflect current STATE values"""
        for i in range(4):
            self.osc_levels[i]['value'] = STATE.osc_mix[i] * 100
            self.osc_waveforms[i].set(STATE.osc_waveforms[i])
            self.osc_detunes[i].set(STATE.osc_detune[i])
        self.cutoff.set(STATE.filter_cutoff)
        self.resonance.set(STATE.filter_res)
        self.filter_type.set(STATE.filter_type)
        for param, slider in self.adsr_sliders.items():
            slider.set(STATE.adsr[param])
        self.gain_slider.set(STATE.master_gain)
        self.pan_slider.set(STATE.master_pan)

    def _update_loop(self):
        """Main update loop for the GUI"""
        update_interval = 1.0 / 30  # 30 FPS refresh rate
        while self.running:
            try:
                if not self.master.winfo_exists():
                    break

                with self.update_lock:
                    # Update visualizations only if window is visible
                    if self.waveform_canvas.get_tk_widget().winfo_viewable():
                        self._update_visualization()
                    
                    # Update GUI elements
                    self._update_gui_elements()
                    
            except tk.TclError as e:
                if "application has been destroyed" in str(e):
                    break
                print(f"Error: {str(e)}")
            time.sleep(update_interval)
            
    def stop(self):
        """Stop the GUI update loop"""
        self.running = False

    def update_midi_device(self, device_name: str):
        pass  # Method removed as midi_label is no longer used

def create_gui():
    """Create and return the main GUI window"""
    root = tk.Tk()
    gui = SynthesizerGUI(root)
    return root, gui
