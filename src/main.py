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
    """Select MIDI input device"""
    midi_devices = mido.get_input_names()
    DEBUG.log(f"\nFound MIDI devices: {midi_devices}")
    
    if not midi_devices:
        DEBUG.log("No MIDI devices found!")
        return None
        
    # Auto-select first device
    selected_device = midi_devices[0]
    DEBUG.log(f"Auto-selected MIDI device: {selected_device}")
    return selected_device

def main():
    """Initialize and run the synthesizer"""
    try:
        # Force Realtek audio device
        output_device = force_realtek_device()
        DEBUG.log(f"Selected audio output device: {output_device}")
        
        # Select MIDI device
        midi_device = select_midi_device()
        DEBUG.log(f"Selected MIDI device: {midi_device}")
        
        # Create synth with forced Realtek device
        synth = Synthesizer(device=output_device)
        DEBUG.log("Synthesizer initialized")
        
        # Create and initialize MIDI handler with device selection
        midi = MIDIHandler(midi_device)
        DEBUG.log("MIDI handler initialized")
        
        # Create NoiseSubModule and set parameters
        noise_sub_module = NoiseSubModule()
        noise_sub_module.set_parameters(noise_amount=0.5, sub_amount=0.5, harmonics=0.5, inharmonicity=0.0)  # Include all required arguments
        DEBUG.log("NoiseSubModule initialized and parameters set")
        
        # Create GUI
        root, gui = create_gui_v2(synth)  # Always use gui_v2
        synth.gui = gui  # Add reference to GUI in the synth instance
        DEBUG.log("GUI created and linked to synthesizer")
        
        # Start the synth engine
        synth.start()
        DEBUG.log("Synth started - ready for MIDI input")
        
        # Connect MIDI callbacks
        def midi_callback(event_type, note, velocity):
            DEBUG.log(f"MIDI callback: {event_type}, Note: {note}, Velocity: {velocity}")
            print(f"MIDI callback: {event_type}, Note: {note}, Velocity: {velocity}")  # Print MIDI callback details
            if event_type == 'note_on':
                synth.note_on(note, velocity)
            elif event_type == 'note_off':
                synth.note_off(note)
        
        # Start MIDI handling
        midi.start(midi_callback)
        DEBUG.log("MIDI handling started")
        
        try:
            # Start GUI main loop
            root.mainloop()
        finally:
            # Cleanup
            synth.stop()
            midi.stop()
            gui.stop()
            DEBUG.log("Cleanup completed")
        
    except Exception as e:
        DEBUG.log(f"An error occurred: {e}")
    finally:
        if 'synth' in locals(): synth.stop()
        if 'midi' in locals(): midi.stop()

if __name__ == "__main__":
    main()
