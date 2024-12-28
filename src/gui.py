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

3. Debug Features:
   - CPU usage monitoring
   - Voice count display
   - Error reporting
   - Module state visualization

4. Real-time Updates:
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
from debug import DEBUG
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class SynthesizerGUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Modular Synthesizer")
        self.update_lock = Lock()
        self.running = True
        
        # Create main containers
        self.create_oscillator_frame()
        self.create_filter_frame()
        self.create_adsr_frame()
        self.create_debug_frame()
        self.create_visualization_frame()
        self.create_module_toggles()
        self.create_debug_display()
        
        # Start update thread
        Thread(target=self._update_loop, daemon=True).start()
        
    def create_oscillator_frame(self):
        frame = ttk.LabelFrame(self.master, text="Oscillators")
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
            
            detune = ttk.Scale(frame, from_=1.0, to=-1.0, length=200)
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
        frame = ttk.LabelFrame(self.master, text="Filter")
        frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        ttk.Label(frame, text="Cutoff").grid(row=0, column=0)
        self.cutoff = ttk.Scale(frame, from_=1.0, to=0.0, length=200)
        self.cutoff.set(STATE.filter_cutoff)
        self.cutoff.grid(row=1, column=0, padx=2, pady=2)
        self.cutoff.configure(command=lambda val: self._update_filter_cutoff(val))
        
        ttk.Label(frame, text="Resonance").grid(row=0, column=1)
        self.resonance = ttk.Scale(frame, from_=1.0, to=0.0, length=200)
        self.resonance.set(STATE.filter_res)
        self.resonance.grid(row=1, column=1, padx=2, pady=2)
        self.resonance.configure(command=lambda val: self._update_filter_res(val))
        
        ttk.Label(frame, text="Type").grid(row=0, column=2)
        self.filter_type = ttk.Combobox(frame, values=['lowpass', 'highpass', 'bandpass'])
        self.filter_type.set(STATE.filter_type)
        self.filter_type.grid(row=1, column=2, padx=2, pady=2)
        self.filter_type.bind("<<ComboboxSelected>>", self._update_filter_type)
        
    def create_adsr_frame(self):
        frame = ttk.LabelFrame(self.master, text="ADSR")
        frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        self.adsr_sliders = {}
        for i, param in enumerate(['attack', 'decay', 'sustain', 'release']):
            ttk.Label(frame, text=param.capitalize()).grid(row=0, column=i)
            slider = ttk.Scale(frame, from_=1.0, to=0.0, length=200)
            slider.set(STATE.adsr[param])
            slider.grid(row=1, column=i, padx=2, pady=2)
            slider.configure(command=lambda val, p=param: self._update_adsr(p, val))
            self.adsr_sliders[param] = slider
            
    def create_debug_frame(self):
        frame = ttk.LabelFrame(self.master, text="Debug")
        frame.grid(row=1, column=1, padx=5, pady=5, sticky="nsew")
        
        # Enhanced bypass controls
        self.bypass_vars = {}
        for i, module in enumerate(STATE.bypass.keys()):
            var = tk.BooleanVar(value=STATE.bypass[module])
            self.bypass_vars[module] = var
            cb = ttk.Checkbutton(
                frame, 
                text=f"Bypass {module}",
                variable=var,
                command=lambda m=module: self._toggle_bypass(m)
            )
            cb.grid(row=i, column=0, sticky="w", padx=5, pady=2)
        
        # Performance metrics
        metrics_frame = ttk.Frame(frame)
        metrics_frame.grid(row=len(STATE.bypass), column=0, sticky="ew", pady=5)
        
        self.perf_label = ttk.Label(metrics_frame, text="CPU: 0.0%")
        self.perf_label.pack(side="left", padx=5)
        
        self.voice_count = ttk.Label(metrics_frame, text="Voices: 0")
        self.voice_count.pack(side="left", padx=5)

        # Add MIDI device info
        self.midi_label = ttk.Label(metrics_frame, text="MIDI: None")
        self.midi_label.pack(side="left", padx=5)

    def create_visualization_frame(self):
        frame = ttk.LabelFrame(self.master, text="Signal Monitoring")
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
        self.spectrum_ax.set_ylim(0, 1)
        self.spectrum_line, = self.spectrum_ax.plot([], [], lw=1, color='red')

    def create_module_toggles(self):
        frame = ttk.LabelFrame(self.master, text="Module Controls")
        frame.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        self.module_vars = {}
        modules = ['Oscillator', 'Filter', 'ADSR', 'GUI Updates', 'MIDI Input', 'Debug Output']
        
        for i, module in enumerate(modules):
            var = tk.BooleanVar(value=True)
            self.module_vars[module] = var
            cb = ttk.Checkbutton(
                frame,
                text=module,
                variable=var,
                command=lambda m=module: self._toggle_module(m)
            )
            cb.grid(row=i//3, column=i%3, padx=5, pady=2, sticky="w")

    def create_debug_display(self):
        frame = ttk.LabelFrame(self.master, text="Debug Output")
        frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")
        
        # Debug text display
        self.debug_text = tk.Text(frame, height=6, width=50, bg='black', fg='green')
        self.debug_text.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        
        # Autoscroll
        self.debug_scroll = ttk.Scrollbar(frame, command=self.debug_text.yview)
        self.debug_text.configure(yscrollcommand=self.debug_scroll.set)
        self.debug_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _toggle_bypass(self, module: str):
        STATE.bypass[module] = self.bypass_vars[module].get()
        
    def _toggle_module(self, module: str):
        state = self.module_vars[module].get()
        self.log_debug(f"Module {module}: {'Enabled' if state else 'Disabled'}")
        # Add specific module handling here

    def log_debug(self, message: str):
        """Add message to debug display"""
        timestamp = time.strftime("%H:%M:%S")
        self.debug_text.insert(tk.END, f"{timestamp} - {message}\n")
        self.debug_text.see(tk.END)  # Autoscroll
        # Keep only last 100 lines
        if int(self.debug_text.index('end-1c').split('.')[0]) > 100:
            self.debug_text.delete('1.0', '2.0')

    def log_state(self):
        """Log the current state to the debug display"""
        state_info = f"""
        Oscillator Mix: {STATE.osc_mix}
        Oscillator Detune: {STATE.osc_detune}
        Oscillator Waveforms: {STATE.osc_waveforms}
        Filter Cutoff: {STATE.filter_cutoff}
        Filter Resonance: {STATE.filter_res}
        Filter Type: {STATE.filter_type}
        ADSR: {STATE.adsr}
        Bypass: {STATE.bypass}
        """
        self.log_debug(state_info)

    def _update_osc_mix(self, value, index):
        STATE.osc_mix[index] = float(value)
        self.osc_levels[index]['value'] = float(value) * 100
        self.log_debug(f"OSC {index+1} mix: {value}")
        
    def _update_osc_detune(self, value, index):
        STATE.osc_detune[index] = float(value)
        self.log_debug(f"OSC {index+1} detune: {value}")
        
    def _update_osc_waveform(self, event, index):
        waveform = event.widget.get()
        STATE.osc_waveforms[index] = waveform
        self.log_debug(f"OSC {index+1} waveform: {waveform}")
        
    def _update_filter_cutoff(self, value):
        STATE.filter_cutoff = float(value)
        self.log_debug(f"Filter cutoff: {value}")
        
    def _update_filter_res(self, value):
        STATE.filter_res = float(value)
        self.log_debug(f"Filter resonance: {value}")
        
    def _update_filter_type(self, event):
        filter_type = event.widget.get()
        STATE.filter_type = filter_type
        self.log_debug(f"Filter type: {filter_type}")
        
    def _update_adsr(self, param, value):
        STATE.adsr[param] = float(value)
        self.log_debug(f"ADSR {param}: {value}")

    def _update_visualization(self):
        """Update waveform and spectrum visualization"""
        signal_data = DEBUG.get_signal_data('audio_out')
        if signal_data:
            print(f"Waveform data: {signal_data[:10]}...")  # Print first 10 data points for debugging
            self._draw_waveform(signal_data)
            self._draw_spectrum(signal_data)
        else:
            print("No signal data available")

    def _draw_waveform(self, data):
        self.waveform_line.set_data(np.arange(len(data)), data)
        self.waveform_ax.set_xlim(0, len(data))
        self.waveform_ax.set_ylim(-1, 1)  # Center the waveform vertically
        self.waveform_canvas.draw()
        print("Waveform updated")

    def _draw_spectrum(self, data):
        spectrum = np.abs(np.fft.fft(data))[:len(data)//2]
        spectrum = spectrum / np.max(spectrum)  # Normalize
        self.spectrum_line.set_data(np.arange(len(spectrum)), spectrum)
        self.spectrum_ax.set_xlim(0, len(spectrum))
        self.spectrum_ax.set_ylim(0, 1)  # Center the spectrum vertically
        self.spectrum_canvas.draw()
        print("Spectrum updated")

    def _update_gui_elements(self):
        """Update GUI elements to reflect current STATE values"""
        for i in range(4):
            self.osc_levels[i]['value'] = STATE.osc_mix[i] * 100
            self.osc_waveforms[i].set(STATE.osc_waveforms[i])
            self.osc_detunes[i].set(STATE.osc_detune[i])
        self.cutoff.set(STATE.filter_cutoff)
        self.resonance.set(STATE.filter_res)
        self.filter_type.set(STATE.filter_type)
        self.log_debug(f"Updated GUI elements")

    def _update_loop(self):
        update_interval = 1.0 / 30  # 30 FPS refresh rate
        while self.running:
            try:
                if not self.module_vars['GUI Updates'].get():
                    time.sleep(update_interval)
                    continue
                    
                with self.update_lock:
                    # Update performance stats
                    cpu_load = DEBUG.get_performance_stats() * 100
                    self.perf_label.configure(text=f"CPU: {cpu_load:.1f}%")
                    
                    # Update visualizations only if window is visible
                    if self.waveform_canvas.get_tk_widget().winfo_viewable():
                        self._update_visualization()
                    
                    # Update voice count
                    active_voices = DEBUG.get_active_voice_count()
                    self.voice_count.configure(text=f"Voices: {active_voices}")
                    
                    # Update GUI elements
                    self._update_gui_elements()
                    
                    # Add debug info
                    if self.module_vars['Debug Output'].get():
                        self.log_debug(f"Active voices: {active_voices}")
                        self.log_debug(f"CPU Load: {cpu_load:.1f}%")
                    
                    # Log the current state
                    self.log_state()
                    
            except Exception as e:
                self.log_debug(f"Error: {str(e)}")
            time.sleep(update_interval)
            
    def stop(self):
        self.running = False

    def update_midi_device(self, device_name: str):
        self.midi_label.configure(text=f"MIDI: {device_name}")

def create_gui():
    root = tk.Tk()
    gui = SynthesizerGUI(root)
    return root, gui
