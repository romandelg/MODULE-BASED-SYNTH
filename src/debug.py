"""
Debug and Monitoring System
----------------------
Provides real-time signal monitoring for debugging purposes.
"""

from collections import deque
import numpy as np
from threading import Lock

class SignalMonitor:
    """Monitors and stores signal data for debugging"""
    
    def __init__(self, buffer_size: int = 1024):
        self.buffer = deque(maxlen=buffer_size)
        self.lock = Lock()
        
    def update(self, values: np.ndarray):
        """Update the buffer with new signal values"""
        with self.lock:
            self.buffer.extend(values.flatten())
            
    def get_data(self) -> np.ndarray:
        """Retrieve the stored signal data"""
        with self.lock:
            return np.array(list(self.buffer)) if self.buffer else np.zeros(1024)

class DebugSystem:
    def __init__(self):
        self.signal_monitors = {
            'audio_out': SignalMonitor(),
            'pre_filter': SignalMonitor(),
            'post_filter': SignalMonitor(),
            'lfo': SignalMonitor(),
            'adsr': SignalMonitor()
        }
        
    def monitor_signal(self, name: str, values: np.ndarray):
        if name in self.signal_monitors:
            self.signal_monitors[name].update(values)
            
    def get_signal_data(self, name: str) -> np.ndarray:
        if name in self.signal_monitors:
            return self.signal_monitors[name].get_data()
        return np.zeros(1024)

DEBUG = DebugSystem()
