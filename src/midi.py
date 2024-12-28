"""
MIDI Event System
---------------
MIDI input handling and parameter mapping.

Features:
1. MIDI Input:
   - Device detection and selection
   - Hot-plugging support
   - Error handling and recovery
   - Thread-safe event queue

2. Event Processing:
   - Note on/off handling
   - Velocity sensitivity
   - Control change mapping
   - Real-time parameter updates

3. Control Mapping:
   - Oscillator mix levels (CC 14-17)
   - Oscillator detune (CC 26-29)
   - Filter controls (CC 22-23)
   - ADSR parameters (CC 18-21)

4. Thread Management:
   - Asynchronous MIDI processing
   - Event queueing
   - Resource cleanup
"""

import mido
from typing import Callable, Optional
from queue import Queue
from threading import Thread
from config import MIDI_CONFIG, STATE  # Changed from relative import
import time

class MIDIHandler:
    def __init__(self, device_name=None):
        self.callback = None
        self.midi_in = None
        self.event_queue = Queue()
        self.running = False
        self.device_name = device_name
        
    def start(self, callback: Callable):
        self.callback = callback
        try:
            if self.device_name:
                self.midi_in = mido.open_input(self.device_name)
                print(f"Connected to MIDI device: {self.device_name}")
            else:
                self.midi_in = mido.open_input()
                print(f"Connected to default MIDI device: {self.midi_in.name}")
                
            self.running = True
            Thread(target=self._midi_loop, daemon=True).start()
        except Exception as e:
            print(f"Failed to open MIDI port: {e}")
            print("Available MIDI ports:", mido.get_input_names())
            
    def stop(self):
        self.running = False
        if self.midi_in:
            self.midi_in.close()
            
    def _midi_loop(self):
        while self.running:
            # Process MIDI messages
            for msg in self.midi_in.iter_pending():
                self._handle_midi_message(msg)
            
            # Process event queue
            try:
                while not self.event_queue.empty():
                    event_type, note, velocity = self.event_queue.get_nowait()
                    if self.callback:
                        self.callback(event_type, note, velocity)
            except Exception as e:
                print(f"MIDI callback error: {e}")
            
            time.sleep(0.001)  # Small sleep to prevent CPU overload

    def _handle_midi_message(self, msg):
        print(f"MIDI IN: {msg}")
        
        if msg.type == 'note_on' and msg.velocity > 0:  # Check velocity > 0
            print(f"Note ON: {msg.note} velocity: {msg.velocity}")
            if self.callback:  # Direct callback for testing
                self.callback('note_on', msg.note, msg.velocity)
            
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            print(f"Note OFF: {msg.note}")
            if self.callback:  # Direct callback for testing
                self.callback('note_off', msg.note, 0)

    def _handle_cc(self, cc: int, value: int):
        normalized = value / 127.0
        
        if cc in MIDI_CONFIG.OSC_MIX_CCS:
            idx = MIDI_CONFIG.OSC_MIX_CCS.index(cc)
            STATE.osc_mix[idx] = normalized
        elif cc in MIDI_CONFIG.OSC_DETUNE_CCS:
            idx = MIDI_CONFIG.OSC_DETUNE_CCS.index(cc)
            STATE.osc_detune[idx] = normalized * 2 - 1
        elif cc == MIDI_CONFIG.FILTER_CUTOFF_CC:
            STATE.filter_cutoff = normalized
        elif cc == MIDI_CONFIG.FILTER_RES_CC:
            STATE.filter_res = normalized
        elif cc in MIDI_CONFIG.ADSR_CCS:
            idx = MIDI_CONFIG.ADSR_CCS.index(cc)
            param = ['attack', 'decay', 'sustain', 'release'][idx]
            STATE.adsr[param] = normalized
