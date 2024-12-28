"""
Main Application Entry Point
--------------------------
System initialization and device management.

Features:
1. Device Management:
   - Audio device detection and selection
   - MIDI device detection and connection
   - Automatic device fallback
   - Device error handling

2. System Initialization:
   - Core synthesizer setup
   - MIDI handler initialization
   - GUI creation and configuration
   - Thread management

3. Resource Management:
   - Clean shutdown handling
   - Resource cleanup
   - Error recovery
   - Device disconnection handling

4. User Interface:
   - Device selection prompts
   - Status messages
   - Error reporting
   - Device information display

Architecture Flow:
1. Device Detection → Selection → Configuration
2. System Initialization → Resource Allocation
3. Main Loop → Event Processing
4. Shutdown → Cleanup
"""

import tkinter as tk
import sounddevice as sd
import mido
from core import Synthesizer
from midi import MIDIHandler
from gui import create_gui
from debug import DEBUG

def force_realtek_device():
    devices = sd.query_devices()
    print("\nAvailable Audio Output Devices:")
    print("-" * 50)
    
    # Find and force Realtek device
    realtek_device = None
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']}")
        if 'Realtek' in device['name'] and device['max_output_channels'] > 0:
            realtek_device = i
            print(f"\nForcing Realtek device: {device['name']}")
            break
    
    if realtek_device is None:
        print("No Realtek device found! Using default")
        return sd.default.device[1]
        
    return realtek_device

def select_midi_device():
    midi_devices = mido.get_input_names()
    if not midi_devices:
        print("No MIDI devices found!")
        return None
        
    print("\nAvailable MIDI Input Devices:")
    print("-" * 50)
    for i, device in enumerate(midi_devices):
        print(f"{i}: {device}")
    
    while True:
        try:
            choice = input("\nSelect MIDI input device (0-{}): ".format(len(midi_devices)-1))
            if choice.strip().lower() == '':
                print("Using first MIDI device")
                return midi_devices[0]
                
            idx = int(choice)
            if 0 <= idx < len(midi_devices):
                print(f"Selected: {midi_devices[idx]}")
                return midi_devices[idx]
        except ValueError:
            print("Please enter a valid number")
        except IndexError:
            print("Please enter a number in the valid range")

def main():
    # Force Realtek audio device
    output_device = force_realtek_device()
    
    # Select MIDI device
    midi_device = select_midi_device()
    
    # Create synth with forced Realtek device
    synth = Synthesizer(device=output_device)
    
    # Create and initialize MIDI handler with device selection
    midi = MIDIHandler(midi_device)
    
    # Create GUI and pass device info
    root, gui = create_gui()
    if midi_device:
        gui.update_midi_device(midi_device)
    
    # Start the synth engine
    synth.start()
    
    # Connect MIDI callbacks
    def midi_callback(event_type, note, velocity):
        if event_type == 'note_on':
            synth.note_on(note, velocity)
        elif event_type == 'note_off':
            synth.note_off(note)
    
    # Start MIDI handling
    midi.start(midi_callback)
    
    try:
        # Start GUI main loop
        root.mainloop()
    finally:
        # Cleanup
        synth.stop()
        midi.stop()
        gui.stop()

if __name__ == "__main__":
    main()
