"""Debug and Monitoring System"""

from collections import deque
import numpy as np
from threading import Lock

class SignalMonitor:
    def __init__(self, buffer_size: int = 1024):
        self.buffer = deque(maxlen=buffer_size)
        self.lock = Lock()
        
    def update(self, values: np.ndarray):
        with self.lock:
            self.buffer.extend(values.flatten())
            
    def get_data(self) -> np.ndarray:
        with self.lock:
            return np.array(list(self.buffer)) if self.buffer else np.zeros(1024)

class DebugSystem:
    def __init__(self):
        self.signal_monitors = {
            'audio_out': SignalMonitor()
        }
        
    def monitor_signal(self, name: str, values: np.ndarray):
        if name in self.signal_monitors:
            self.signal_monitors[name].update(values)
            
    def get_signal_data(self, name: str) -> np.ndarray:
        if name in self.signal_monitors:
            return self.signal_monitors[name].get_data()
        return np.zeros(1024)

DEBUG = DebugSystem()
