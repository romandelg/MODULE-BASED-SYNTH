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
        
        # Start update thread
        Thread(target=self._update_loop, daemon=True).start()
        
    def create_oscillator_frame(self):
        frame = ttk.LabelFrame(self.master, text="Oscillators")
        frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        self.osc_levels = []
        for i in range(4):
            label = ttk.Label(frame, text=f"OSC {i+1}")
            label.grid(row=0, column=i, padx=2)
            
            level = ttk.Scale(frame, from_=1.0, to=0.0, length=200)
            level.set(STATE.osc_mix[i])
            level.grid(row=1, column=i, padx=2, pady=2)
            self.osc_levels.append(level)
            
            detune = ttk.Scale(frame, from_=1.0, to=-1.0, length=200)
            detune.set(STATE.osc_detune[i])
            detune.grid(row=2, column=i, padx=2, pady=2)
            
    def create_filter_frame(self):
        frame = ttk.LabelFrame(self.master, text="Filter")
        frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        ttk.Label(frame, text="Cutoff").grid(row=0, column=0)
        self.cutoff = ttk.Scale(frame, from_=1.0, to=0.0, length=200)
        self.cutoff.set(STATE.filter_cutoff)
        self.cutoff.grid(row=1, column=0, padx=2, pady=2)
        
        ttk.Label(frame, text="Resonance").grid(row=0, column=1)
        self.resonance = ttk.Scale(frame, from_=1.0, to=0.0, length=200)
        self.resonance.set(STATE.filter_res)
        self.resonance.grid(row=1, column=1, padx=2, pady=2)
        
    def create_adsr_frame(self):
        frame = ttk.LabelFrame(self.master, text="ADSR")
        frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")
        
        self.adsr_sliders = {}
        for i, param in enumerate(['attack', 'decay', 'sustain', 'release']):
            ttk.Label(frame, text=param.capitalize()).grid(row=0, column=i)
            slider = ttk.Scale(frame, from_=1.0, to=0.0, length=200)
            slider.set(STATE.adsr[param])
            slider.grid(row=1, column=i, padx=2, pady=2)
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
        
        self.waveform_canvas = tk.Canvas(frame, width=400, height=100, bg='black')
        self.waveform_canvas.grid(row=0, column=0, padx=5, pady=5)
        
        self.spectrum_canvas = tk.Canvas(frame, width=400, height=100, bg='black')
        self.spectrum_canvas.grid(row=1, column=0, padx=5, pady=5)

    def _toggle_bypass(self, module: str):
        STATE.bypass[module] = self.bypass_vars[module].get()
        
    def _update_visualization(self):
        # Update waveform display
        signal_data = DEBUG.get_signal_data('audio_out')
        if signal_data:
            self._draw_waveform(signal_data)
            self._draw_spectrum(signal_data)

    def _draw_waveform(self, data):
        self.waveform_canvas.delete("all")
        if not data:
            return
            
        width = self.waveform_canvas.winfo_width()
        height = self.waveform_canvas.winfo_height()
        points = []
        
        for i, value in enumerate(data):
            x = i * width / len(data)
            y = height/2 * (1 - value)
            points.extend([x, y])
            
        if len(points) >= 4:
            self.waveform_canvas.create_line(points, fill='#00ff00', width=1)

    def _draw_spectrum(self, data):
        # Similar to _draw_waveform but for frequency spectrum
        # Using numpy.fft.fft for spectrum analysis
        pass

    def _update_loop(self):
        update_interval = 1.0 / 15  # Reduced to 15 FPS
        while self.running:
            try:
                with self.update_lock:
                    # Update performance stats
                    cpu_load = DEBUG.get_performance_stats() * 100
                    self.perf_label.configure(text=f"CPU: {cpu_load:.1f}%")
                    
                    # Update visualizations only if window is visible
                    if self.waveform_canvas.winfo_viewable():
                        self._update_visualization()
                    
                    # Update voice count
                    active_voices = DEBUG.get_active_voice_count()
                    self.voice_count.configure(text=f"Voices: {active_voices}")
                    
            except Exception as e:
                DEBUG.log_error("GUI update error", e)
                
            time.sleep(update_interval)
            
    def stop(self):
        self.running = False

    def update_midi_device(self, device_name: str):
        self.midi_label.configure(text=f"MIDI: {device_name}")

def create_gui():
    root = tk.Tk()
    gui = SynthesizerGUI(root)
    return root, gui
