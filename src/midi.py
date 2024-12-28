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
import time
import logging
from typing import Callable, Optional, Dict
from queue import Queue
from threading import Thread, Lock
from config import MIDI_CONFIG, STATE
from debug import DEBUG

class MIDIEvent:
    def __init__(self, type: str, data: Dict):
        self.type = type
        self.data = data
        self.timestamp = time.time()

class MIDIHandler:
    def __init__(self, device_name=None):
        self.callback = None
        self.midi_in = None
        self.event_queue = Queue()
        self.running = False
        self.device_name = device_name
        self.lock = Lock()
        self.last_cc_values = {}  # Cache for CC values
        self.reconnect_interval = 1.0  # Seconds between reconnection attempts
        self.last_reconnect_attempt = 0
        self.available_ports = set()
        
    def start(self, callback: Callable):
        """Start MIDI processing with callback for events"""
        self.callback = callback
        self.running = True
        # Start device monitoring thread
        Thread(target=self._device_monitor, daemon=True).start()
        self._connect_midi()
            
    def stop(self):
        """Clean shutdown of MIDI processing"""
        self.running = False
        if self.midi_in:
            self.midi_in.close()
            
    def _connect_midi(self) -> bool:
        """Attempt to connect to MIDI device"""
        try:
            if self.midi_in:
                self.midi_in.close()
                
            if self.device_name:
                self.midi_in = mido.open_input(self.device_name)
                DEBUG.log_info(f"Connected to MIDI device: {self.device_name}")
            else:
                ports = mido.get_input_names()
                if ports:
                    self.midi_in = mido.open_input(ports[0])
                    self.device_name = ports[0]
                    DEBUG.log_info(f"Connected to default MIDI device: {self.midi_in.name}")
                else:
                    raise RuntimeError("No MIDI devices found")
                    
            Thread(target=self._midi_loop, daemon=True).start()
            Thread(target=self._event_processor, daemon=True).start()
            return True
            
        except Exception as e:
            DEBUG.log_error("Failed to open MIDI port", e)
            return False
            
    def _device_monitor(self):
        """Monitor MIDI devices for hot-plugging"""
        while self.running:
            try:
                current_ports = set(mido.get_input_names())
                
                # Check for new devices
                new_ports = current_ports - self.available_ports
                if new_ports and not self.midi_in:
                    DEBUG.log_info(f"New MIDI devices detected: {new_ports}")
                    self._connect_midi()
                
                # Check for disconnected devices
                if self.midi_in and self.device_name not in current_ports:
                    DEBUG.log_error(f"MIDI device {self.device_name} disconnected")
                    self.midi_in = None
                    self._attempt_reconnect()
                    
                self.available_ports = current_ports
                    
            except Exception as e:
                DEBUG.log_error("Device monitoring error", e)
                
            time.sleep(1.0)  # Check every second
            
    def _attempt_reconnect(self):
        """Attempt to reconnect to MIDI device"""
        current_time = time.time()
        if current_time - self.last_reconnect_attempt >= self.reconnect_interval:
            self.last_reconnect_attempt = current_time
            if self._connect_midi():
                DEBUG.log_info("Successfully reconnected to MIDI device")
            
    def _midi_loop(self):
        """Main MIDI message processing loop"""
        while self.running:
            try:
                for msg in self.midi_in.iter_pending():
                    self._handle_midi_message(msg)
                time.sleep(0.001)  # Prevent CPU overload
            except Exception as e:
                DEBUG.log_error("MIDI processing error", e)
                
    def _event_processor(self):
        """Separate thread for event queue processing"""
        while self.running:
            try:
                if not self.event_queue.empty():
                    event = self.event_queue.get_nowait()
                    if event.type == 'note_on':
                        self.callback('note_on', event.data['note'], event.data['velocity'])
                    elif event.type == 'note_off':
                        self.callback('note_off', event.data['note'], 0)
                time.sleep(0.001)
            except Exception as e:
                DEBUG.log_error("Event processing error", e)

    def _handle_midi_message(self, msg):
        """Process incoming MIDI messages with error recovery"""
        DEBUG.log_debug(f"MIDI IN: {msg}")
        
        try:
            if msg.type == 'note_on':
                if msg.velocity > 0:
                    self.event_queue.put(MIDIEvent('note_on', {
                        'note': msg.note,
                        'velocity': msg.velocity
                    }))
                else:  # Note off with velocity 0
                    self.event_queue.put(MIDIEvent('note_off', {
                        'note': msg.note
                    }))
                    
            elif msg.type == 'note_off':
                self.event_queue.put(MIDIEvent('note_off', {
                    'note': msg.note
                }))
                
            elif msg.type == 'control_change':
                self._handle_cc(msg.control, msg.value)
                
            elif msg.type == 'pitchwheel':
                self._handle_pitch_bend(msg.pitch)
                
        except Exception as e:
            DEBUG.log_error("MIDI message handling error", e)
            # Attempt recovery
            if "port closed" in str(e).lower():
                self._attempt_reconnect()
            elif "buffer overflow" in str(e).lower():
                self.event_queue = Queue()  # Clear queue

    def _handle_cc(self, cc: int, value: int):
        """Handle MIDI Control Change messages"""
        with self.lock:
            # Avoid processing duplicate values
            if cc in self.last_cc_values and self.last_cc_values[cc] == value:
                return
                
            self.last_cc_values[cc] = value
            normalized = value / 127.0
            
            try:
                if cc in MIDI_CONFIG.OSC_MIX_CCS:
                    idx = MIDI_CONFIG.OSC_MIX_CCS.index(cc)
                    STATE.osc_mix[idx] = normalized
                    DEBUG.log_debug(f"OSC {idx+1} mix: {normalized:.2f}")
                    
                elif cc in MIDI_CONFIG.OSC_DETUNE_CCS:
                    idx = MIDI_CONFIG.OSC_DETUNE_CCS.index(cc)
                    STATE.osc_detune[idx] = normalized * 2 - 1
                    DEBUG.log_debug(f"OSC {idx+1} detune: {STATE.osc_detune[idx]:.2f}")
                    
                elif cc == MIDI_CONFIG.FILTER_CUTOFF_CC:
                    STATE.filter_cutoff = normalized
                    DEBUG.log_debug(f"Filter cutoff: {normalized:.2f}")
                    
                elif cc == MIDI_CONFIG.FILTER_RES_CC:
                    STATE.filter_res = normalized
                    DEBUG.log_debug(f"Filter resonance: {normalized:.2f}")
                    
                elif cc in MIDI_CONFIG.ADSR_CCS:
                    idx = MIDI_CONFIG.ADSR_CCS.index(cc)
                    param = ['attack', 'decay', 'sustain', 'release'][idx]
                    STATE.adsr[param] = normalized
                    DEBUG.log_debug(f"ADSR {param}: {normalized:.2f}")
                    
            except Exception as e:
                DEBUG.log_error(f"CC handling error: CC={cc}, value={value}", e)

    def _handle_pitch_bend(self, value: int):
        """Handle MIDI pitch bend messages"""
        normalized = (value + 8192) / 16383.0  # Convert to 0-1 range
        DEBUG.log_debug(f"Pitch bend: {normalized:.2f}")
        # Add pitch bend handling if needed

    def cleanup(self):
        """Thorough resource cleanup"""
        self.running = False
        if self.midi_in:
            try:
                self.midi_in.close()
            except:
                pass
        self.midi_in = None
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except:
                break
        self.last_cc_values.clear()
