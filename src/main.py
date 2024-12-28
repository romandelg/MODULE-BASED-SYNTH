"""
Main Application Entry
-------------------
- Audio device setup
- MIDI device setup
- Basic error handling
"""

import tkinter as tk
import sounddevice as sd
import mido
from core import Synthesizer
from midi import MIDIHandler
from gui import create_gui
from debug import DEBUG

def force_realtek_device():
    """Force the use of a Realtek audio device if available"""
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
    """Prompt the user to select a MIDI input device"""
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
    """Initialize and run the synthesizer"""
    try:
        # Force Realtek audio device
        output_device = force_realtek_device()
        
        # Select MIDI device
        midi_device = select_midi_device()
        print(f"Selected MIDI device: {midi_device}")  # Debugging statement
        
        # Create synth with forced Realtek device
        synth = Synthesizer(device=output_device)
        
        # Create and initialize MIDI handler with device selection
        midi = MIDIHandler(midi_device)
        
        # Create GUI
        root, gui = create_gui()
        
        # Start the synth engine
        synth.start()
        print("Synth started - ready for MIDI input")
        
        # Connect MIDI callbacks
        def midi_callback(event_type, note, velocity):
            print(f"MIDI callback: {event_type}, Note: {note}, Velocity: {velocity}")  # Debugging statement
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
        
    finally:
        if 'synth' in locals(): synth.stop()
        if 'midi' in locals(): midi.stop()

if __name__ == "__main__":
    main()
