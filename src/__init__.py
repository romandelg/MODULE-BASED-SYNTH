"""
Modular Polyphonic Synthesizer
-----------------------------
A real-time modular synthesizer with MIDI support.

Public Modules:
    core: Synthesizer engine and voice management
    midi: MIDI input handling
    audio: Sound generation and processing
    gui: User interface and visualization
"""

__version__ = '1.0.0'
__author__ = 'Your Name'

# Expose main classes for easier imports
from .core import Synthesizer
from .midi import MIDIHandler
from .gui import create_gui
from .config import STATE, AUDIO_CONFIG, MIDI_CONFIG

# Define what gets imported with 'from synthesizer import *'
__all__ = [
    'Synthesizer',
    'MIDIHandler',
    'create_gui',
    'STATE',
    'AUDIO_CONFIG',
    'MIDI_CONFIG'
]
