"""
MIDI Event System
-----------------
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
import time
from typing import Callable
from queue import Queue
from threading import Thread, Lock
from config import MIDI_CONFIG, STATE
from debug import DEBUG

class MIDIHandler:
    """Handles MIDI input and maps events to synthesizer parameters"""
    
    def __init__(self, device_name=None):
        self.callback = None
        self.midi_in = None
        self.event_queue = Queue()
        self.running = False
        self.device_name = device_name
        self.lock = Lock()
        
    def start(self, callback: Callable):
        """Start the MIDI handler with the given callback"""
        self.callback = callback
        self.running = True
        Thread(target=self._midi_loop, daemon=True).start()
        self._connect_midi()
            
    def stop(self):
        """Stop the MIDI handler"""
        self.running = False
        if self.midi_in:
            self.midi_in.close()
            
    def _connect_midi(self) -> bool:
        """Connect to the MIDI device"""
        try:
            if self.midi_in:
                self.midi_in.close()
                
            ports = mido.get_input_names()
            if self.device_name and self.device_name in ports:
                self.midi_in = mido.open_input(self.device_name)
            elif ports:
                self.midi_in = mido.open_input(ports[0])
                self.device_name = ports[0]
            else:
                return False
            DEBUG.log(f"Connected to MIDI device: {self.device_name}")
            return True
            
        except Exception as e:
            DEBUG.log(f"Failed to connect to MIDI device: {e}")
            return False
            
    def _midi_loop(self):
        """Main loop for processing MIDI events"""
        while self.running:
            try:
                if not self.midi_in:
                    if not self._connect_midi():
                        time.sleep(1.0)
                        continue

                for msg in self.midi_in.iter_pending():
                    self._handle_midi_message(msg)
                time.sleep(0.001)
                
            except Exception as e:
                DEBUG.log(f"Error in MIDI loop: {e}")
                self.midi_in = None

    def _handle_midi_message(self, msg):
        """Handle incoming MIDI messages"""
        try:
            DEBUG.log(f"Received MIDI message: {msg}")
            if msg.type == 'note_on' and msg.velocity > 0:
                self.callback('note_on', msg.note, msg.velocity)
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                self.callback('note_off', msg.note, 0)
            elif msg.type == 'control_change':
                self._handle_cc(msg.control, msg.value)
        except Exception as e:
            DEBUG.log(f"Error handling MIDI message: {e}")

    def _handle_cc(self, cc: int, value: int):
        """Handle MIDI control change messages"""
        with self.lock:
            normalized = value / 127.0
            try:
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
                elif cc == 24:  # LFO Frequency
                    STATE.lfo_frequency = normalized * 20  # Scale to 0.1 - 20 Hz
                elif cc == 25:  # LFO Depth
                    STATE.lfo_depth = normalized * 2  # Scale to 0.0 - 2.0
                DEBUG.log(f"Handled CC message: CC={cc}, Value={value}, Normalized={normalized}")
            except Exception as e:
                DEBUG.log(f"Error handling CC message: {e}")
                pass
