"""
Main Application Entry
----------------------
- Audio device setup
- MIDI device setup
- Basic error handling
"""

import tkinter as tk
import sounddevice as sd
import mido
from core import Synthesizer
from midi import MIDIHandler
from gui_v2 import create_gui_v2
from debug import DEBUG
from noise_sub_module import NoiseSubModule

def force_realtek_device():
    """Force the use of a Realtek audio device if available"""
    devices = sd.query_devices()
    DEBUG.log("\nAvailable Audio Output Devices:")
    DEBUG.log("-" * 50)
    
    # Find and force Realtek device
    realtek_device = None
    for i, device in enumerate(devices):
        DEBUG.log(f"{i}: {device['name']}")
        if 'Realtek' in device['name'] and device['max_output_channels'] > 0:
            realtek_device = i
            DEBUG.log(f"\nForcing Realtek device: {device['name']}")
            break
    
    if realtek_device is None:
        DEBUG.log("No Realtek device found! Using default")
        return sd.default.device[1]
        
    return realtek_device

def select_midi_device():
    """Prompt the user to select a MIDI input device"""
    midi_devices = mido.get_input_names()
    if not midi_devices:
        DEBUG.log("No MIDI devices found!")
        return None
        
    DEBUG.log("\nAvailable MIDI Input Devices:")
    DEBUG.log("-" * 50)
    for i, device in enumerate(midi_devices):
        DEBUG.log(f"{i}: {device}")
    
    while True:
        try:
            choice = input("\nSelect MIDI input device (0-{}): ".format(len(midi_devices)-1))
            if choice.strip().lower() == '':
                DEBUG.log("Using first MIDI device")
                return midi_devices[0]
                
            idx = int(choice)
            if 0 <= idx < len(midi_devices):
                DEBUG.log(f"Selected: {midi_devices[idx]}")
                return midi_devices[idx]
        except ValueError:
            DEBUG.log("Please enter a valid number")
        except IndexError:
            DEBUG.log("Please enter a number in the valid range")

def main():
    """Initialize and run the synthesizer"""
    try:
        # Force Realtek audio device
        output_device = force_realtek_device()
        
        # Select MIDI device
        midi_device = select_midi_device()
        DEBUG.log(f"Selected MIDI device: {midi_device}")
        
        # Create synth with forced Realtek device
        synth = Synthesizer(device=output_device)
        
        # Create and initialize MIDI handler with device selection
        midi = MIDIHandler(midi_device)
        
        # Create NoiseSubModule and set parameters
        noise_sub_module = NoiseSubModule()
        noise_sub_module.set_parameters(noise_amount=0.5, sub_amount=0.5, harmonics=0.5, inharmonicity=0.0)  # Include all required arguments
        
        # Create GUI
        root, gui = create_gui_v2(synth)  # Always use gui_v2
        synth.gui = gui  # Add reference to GUI in the synth instance
        
        # Start the synth engine
        synth.start()
        DEBUG.log("Synth started - ready for MIDI input")
        
        # Connect MIDI callbacks
        def midi_callback(event_type, note, velocity):
            DEBUG.log(f"MIDI callback: {event_type}, Note: {note}, Velocity: {velocity}")
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
        
    except Exception as e:
        DEBUG.log(f"An error occurred: {e}")
    finally:
        if 'synth' in locals(): synth.stop()
        if 'midi' in locals(): midi.stop()

if __name__ == "__main__":
    main()
