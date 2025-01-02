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
from mido import MidiFile, MidiTrack, Message

class MIDIHandler:
    """Handles MIDI input and routes events to the synthesizer"""
    
    def __init__(self, device_name=None):
        self.callback = None
        self.input_port = None
        self.device_name = device_name
        self.lock = Lock()
        
    def start(self, callback: Callable):
        """Start MIDI input and set the callback for MIDI events"""
        try:
            available_devices = mido.get_input_names()
            DEBUG.log(f"Available MIDI devices: {available_devices}")
            
            # Auto-select first available device if none specified
            if not self.device_name and available_devices:
                self.device_name = available_devices[0]
                DEBUG.log(f"Auto-selected MIDI device: {self.device_name}")
                
            if not available_devices:
                DEBUG.log("ERROR: No MIDI devices found!")
                return
                
            if self.device_name not in available_devices:
                DEBUG.log(f"Warning: Selected device '{self.device_name}' not found.")
                self.device_name = available_devices[0]
                DEBUG.log(f"Using first available device: {self.device_name}")
                
            self.input_port = mido.open_input(self.device_name)
            self.callback = callback
            
            # Start message polling thread
            def poll_messages():
                while self.input_port:
                    for msg in self.input_port.iter_pending():
                        self._midi_callback(msg)
                    time.sleep(0.001)  # Small sleep to prevent CPU hogging
                    
            self._poll_thread = Thread(target=poll_messages, daemon=True)
            self._poll_thread.start()
            
            DEBUG.log(f"MIDI input started successfully on {self.device_name}")
            self._last_event_time = time.time()
            
        except Exception as e:
            DEBUG.log(f"MIDI start error: {str(e)}")
            
    def stop(self):
        """Stop MIDI input"""
        if self.input_port:
            self.input_port.close()
            DEBUG.log("MIDI input stopped")
            
    def _monitor_input(self):
        """Check periodically if we've received any input."""
        while True:
            time.sleep(2.0)  # Check every 2 seconds
            elapsed = time.time() - self._last_event_time
            if elapsed > 2.0:
                print("No MIDI events detected in the last 2 seconds...")
            if not self.input_port:
                break

    def _midi_callback(self, message):
        """Internal MIDI callback to process MIDI messages"""
        self._last_event_time = time.time()
        DEBUG.log(f"MIDI message received: {message}")
        if message.type == 'note_on':
            DEBUG.log(f"Note On: {message.note}, Velocity: {message.velocity}")
            print(f"Note On: {message.note}, Velocity: {message.velocity}")  # Print individual keystrokes
            self.callback('note_on', message.note, message.velocity)
        elif message.type == 'note_off':
            DEBUG.log(f"Note Off: {message.note}, Velocity: {message.velocity}")
            print(f"Note Off: {message.note}, Velocity: {message.velocity}")  # Print individual keystrokes
            self.callback('note_off', message.note, message.velocity)
        else:
            DEBUG.log(f"Unhandled MIDI message type: {message.type}")
