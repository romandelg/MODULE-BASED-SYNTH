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
import numpy as np
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
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Modular Synthesizer")
        self.update_lock = Lock()
        self.running = True
        
        # Create main containers
        self.create_scrollable_area()
        self.create_oscillator_frame()
        self.create_filter_frame()
        self.create_adsr_frame()
        self.create_visualization_frame()
        
        # Start update thread
        Thread(target=self._update_loop, daemon=True).start()

    def create_scrollable_area(self):
        self.canvas = tk.Canvas(self.master)
        self.scrollbar = ttk.Scrollbar(self.master, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def create_oscillator_frame(self):
        frame = ttk.LabelFrame(self.scrollable_frame, text="Oscillators")
        frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.osc_levels = []
        self.osc_detunes = []
        self.osc_waveforms = []
        for i in range(4):
            label = ttk.Label(frame, text=f"OSC {i+1}")
            label.grid(row=0, column=i, padx=2)
            
            level = ttk.Progressbar(frame, orient="vertical", length=200, mode="determinate")
            level['value'] = STATE.osc_mix[i] * 100
            level.grid(row=1, column=i, padx=2, pady=2)
            self.osc_levels.append(level)
            
            detune = ttk.Scale(frame, from_=1.0, to=-1.0, length=200, orient="vertical")
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
        frame = ttk.LabelFrame(self.scrollable_frame, text="Filter")
        frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        ttk.Label(frame, text="Cutoff").grid(row=0, column=0)
        self.cutoff = ttk.Scale(frame, from_=1.0, to=0.0, length=200, orient="vertical")
        self.cutoff.set(STATE.filter_cutoff)
        self.cutoff.grid(row=1, column=0, padx=2, pady=2)
        self.cutoff.configure(command=lambda val: self._update_filter_cutoff(val))
        
        ttk.Label(frame, text="Resonance").grid(row=0, column=1)
        self.resonance = ttk.Scale(frame, from_=1.0, to=0.0, length=200, orient="vertical")
        self.resonance.set(STATE.filter_res)
        self.resonance.grid(row=1, column=1, padx=2, pady=2)
        self.resonance.configure(command=lambda val: self._update_filter_res(val))
        
        ttk.Label(frame, text="Type").grid(row=0, column=2)
        self.filter_type = ttk.Combobox(frame, values=['lowpass', 'highpass', 'bandpass'])
        self.filter_type.set(STATE.filter_type)
        self.filter_type.grid(row=1, column=2, padx=2, pady=2)
        self.filter_type.bind("<<ComboboxSelected>>", self._update_filter_type)
        
    def create_adsr_frame(self):
        frame = ttk.LabelFrame(self.scrollable_frame, text="ADSR")
        frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        self.adsr_sliders = {}
        for i, param in enumerate(['attack', 'decay', 'sustain', 'release']):
            ttk.Label(frame, text=param.capitalize()).grid(row=0, column=i)
            slider = ttk.Scale(frame, from_=1.0, to=0.0, length=200, orient="vertical")
            slider.set(STATE.adsr[param])
            slider.grid(row=1, column=i, padx=2, pady=2)
            slider.configure(command=lambda val, p=param: self._update_adsr(p, val))
            self.adsr_sliders[param] = slider

    def create_visualization_frame(self):
        frame = ttk.LabelFrame(self.scrollable_frame, text="Signal Monitoring")
        frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        # Create waveform plot
        self.waveform_fig, self.waveform_ax = plt.subplots(figsize=(5, 2))
        self.waveform_canvas = FigureCanvasTkAgg(self.waveform_fig, master=frame)
        self.waveform_canvas.get_tk_widget().grid(row=0, column=0, padx=5, pady=5)
        self.waveform_ax.set_title("Waveform")
        self.waveform_ax.set_xlim(0, 1024)
        self.waveform_ax.set_ylim(-1, 1)
        self.waveform_line, = self.waveform_ax.plot([], [], lw=1, color='red')
        
        # Create spectrum plot
        self.spectrum_fig, self.spectrum_ax = plt.subplots(figsize=(5, 2))
        self.spectrum_canvas = FigureCanvasTkAgg(self.spectrum_fig, master=frame)
        self.spectrum_canvas.get_tk_widget().grid(row=1, column=0, padx=5, pady=5)
        self.spectrum_ax.set_title("Spectrum")
        self.spectrum_ax.set_xlim(0, 512)
        self.spectrum_ax.set_ylim(0, 200)  # Update y-axis limit to 200
        self.spectrum_line, = self.spectrum_ax.plot([], [], lw=1, color='red')

    def _update_osc_mix(self, value, index):
        STATE.osc_mix[index] = float(value)
        self.osc_levels[index]['value'] = float(value) * 100
        
    def _update_osc_detune(self, value, index):
        STATE.osc_detune[index] = float(value)
        
    def _update_osc_waveform(self, event, index):
        waveform = event.widget.get()
        STATE.osc_waveforms[index] = waveform
        
    def _update_filter_cutoff(self, value):
        STATE.filter_cutoff = float(value)
        
    def _update_filter_res(self, value):
        STATE.filter_res = float(value)
        
    def _update_filter_type(self, event):
        filter_type = event.widget.get()
        STATE.filter_type = filter_type
        
    def _update_adsr(self, param, value):
        STATE.adsr[param] = float(value)

    def _update_visualization(self):
        """Update waveform and spectrum visualization"""
        signal_data = DEBUG.get_signal_data('audio_out')
        if signal_data:
            self._draw_waveform(signal_data)
            self._draw_spectrum(signal_data)

    def _draw_waveform(self, data):
        self.waveform_line.set_data(np.arange(len(data)), data)
        self.waveform_ax.set_xlim(0, len(data))
        self.waveform_ax.set_ylim(-1, 1)  # Center the waveform vertically
        self.waveform_canvas.draw()

    def _draw_spectrum(self, data):
        spectrum = np.abs(np.fft.fft(data))[:len(data)//2]
        spectrum = spectrum / np.max(spectrum) * 200  # Normalize to fit within 0-200 range
        self.spectrum_line.set_data(np.arange(len(spectrum)), spectrum)
        self.spectrum_ax.set_xlim(0, len(spectrum))
        self.spectrum_ax.set_ylim(0, 200)  # Center the spectrum vertically
        self.spectrum_canvas.draw()

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

    def _update_loop(self):
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
        self.running = False

    def update_midi_device(self, device_name: str):
        pass  # Method removed as midi_label is no longer used

def create_gui():
    root = tk.Tk()
    gui = SynthesizerGUI(root)
    return root, gui
