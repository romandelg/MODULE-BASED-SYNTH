"""
Debug and Monitoring System
-------------------------
Performance tracking and system monitoring.

Features:
1. Performance Monitoring:
   - CPU usage tracking
   - Buffer underrun detection
   - Processing time measurement
   - Memory usage tracking

2. Signal Monitoring:
   - Audio level metering
   - Signal path visualization
   - Module state tracking
   - Real-time statistics

3. Error Handling:
   - Exception logging
   - Error reporting
   - Stack trace capture
   - Recovery strategies

4. Development Tools:
   - Module profiling
   - Signal flow analysis
   - Parameter validation
   - State verification
"""

import time
import logging
from typing import Dict
from threading import Lock
from collections import deque
import numpy as np

class PerformanceMonitor:
    def __init__(self, window_size: int = 100):
        self.times = deque(maxlen=window_size)
        self.lock = Lock()
        
    def measure(self) -> float:
        with self.lock:
            return sum(self.times) / len(self.times) if self.times else 0
            
    def add_measurement(self, duration: float):
        with self.lock:
            self.times.append(duration)

class SignalMonitor:
    def __init__(self, buffer_size: int = 1024):
        self.buffer = deque(maxlen=buffer_size)
        self.lock = Lock()
        
    def update(self, values: np.ndarray):
        with self.lock:
            self.buffer.extend(values)
            
    def get_data(self) -> list:
        with self.lock:
            return list(self.buffer)

class DebugSystem:
    def __init__(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.perf_monitor = PerformanceMonitor()
        self.signal_monitors: Dict[str, SignalMonitor] = {
            'audio_out': SignalMonitor(),
            'filter_out': SignalMonitor(),
            'envelope': SignalMonitor()
        }
        self.signal_monitors.update({
            'oscillator_out': SignalMonitor(),
            'filter_in': SignalMonitor(),
            'filter_out': SignalMonitor(),
            'envelope_out': SignalMonitor(),
            'master_out': SignalMonitor(),
        })
        self.voice_count = 0
        self.module_timings = {}
        
    def start_measurement(self) -> float:
        return time.perf_counter()
        
    def end_measurement(self, start_time: float, label: str):
        duration = time.perf_counter() - start_time
        self.perf_monitor.add_measurement(duration)
        logging.debug(f"{label}: {duration*1000:.2f}ms")
        
    def log_info(self, message: str):
        """Log information message"""
        logging.info(message)
        
    def log_debug(self, message: str):
        """Log debug message"""
        logging.debug(message)
        
    def log_error(self, message: str, exception: Exception = None):
        """Log error message with optional exception"""
        if exception:
            logging.error(f"{message}: {str(exception)}")
        else:
            logging.error(message)
        
    def log_warning(self, message: str):
        """Log warning message"""
        logging.warning(message)
            
    def monitor_signal(self, name: str, values: np.ndarray):
        if name in self.signal_monitors:
            self.signal_monitors[name].update(values)
            
    def get_signal_data(self, name: str) -> list:
        if name in self.signal_monitors:
            return self.signal_monitors[name].get_data()
        return []
        
    def get_performance_stats(self) -> float:
        return self.perf_monitor.measure()

    def monitor_module(self, name: str, input_signal: np.ndarray, output_signal: np.ndarray):
        """Monitor input/output of a module for debugging"""
        self.signal_monitors[f"{name}_in"].update(np.mean(np.abs(input_signal)))
        self.signal_monitors[f"{name}_out"].update(np.mean(np.abs(output_signal)))

    def track_voices(self, active_count: int):
        """Track number of active voices"""
        self.voice_count = active_count

    def get_active_voice_count(self) -> int:
        return self.voice_count

    def profile_module(self, module_name: str):
        """Decorator for profiling module performance"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start = self.start_measurement()
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                self.module_timings[module_name] = duration
                return result
            return wrapper
        return decorator

    def get_module_timings(self) -> Dict[str, float]:
        """Get performance timings for all modules"""
        return self.module_timings.copy()

    def monitor_signal_flow(self, module_name: str, signal: np.ndarray):
        """Monitor signal flow through modules"""
        if signal is not None:
            stats = {
                'min': float(np.min(signal)),
                'max': float(np.max(signal)),
                'rms': float(np.sqrt(np.mean(signal**2))),
                'peak': float(np.max(np.abs(signal)))
            }
            logging.debug(f"{module_name} stats: {stats}")

# Global debug instance
DEBUG = DebugSystem()
