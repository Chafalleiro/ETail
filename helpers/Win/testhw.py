import clr
import os
import ctypes
# Load the DLL
dll = ctypes.CDLL(os.path.abspath(os.path.dirname(__file__)) + R'\LibreHardwareMonitorLib.dll')
# List functions (you need to know the function names)
functions = dir(dll)
print(functions)


clr.AddReference(os.path.abspath(os.path.dirname(__file__)) + R'\LibreHardwareMonitorLib.dll')
from LibreHardwareMonitor import Hardware

def get_specific_metrics():
    hw = Hardware.Computer()
    hw.IsCpuEnabled = True
    hw.IsGpuEnabled = True 
    hw.IsMemoryEnabled = True
    hw.IsMotherboardEnabled = True
    hw.IsStorageEnabled = True
    hw.Open()
    
    metrics = {}
    
    for hardware in hw.Hardware:
        hardware.Update()
        
        # CPU Temperature and Load
        if hardware.HardwareType == Hardware.HardwareType.Cpu:
            for sensor in hardware.Sensors:
                if sensor.SensorType == Hardware.SensorType.Temperature and "Core" in sensor.Name:
                    metrics['cpu_temp'] = sensor.Value
                elif sensor.SensorType == Hardware.SensorType.Load and "CPU Total" in sensor.Name:
                    metrics['cpu_load'] = sensor.Value
                elif sensor.SensorType == Hardware.SensorType.Clock and "Bus Speed" in sensor.Name:
                    metrics['bus_speed'] = sensor.Value
        
        # GPU Temperature and Load        
        elif hardware.HardwareType in [Hardware.HardwareType.GpuNvidia, 
                                      Hardware.HardwareType.GpuAmd, 
                                      Hardware.HardwareType.GpuIntel]:
            for sensor in hardware.Sensors:
                if sensor.SensorType == Hardware.SensorType.Temperature:
                    metrics['gpu_temp'] = sensor.Value
                elif sensor.SensorType == Hardware.SensorType.Load and "GPU Core" in sensor.Name:
                    metrics['gpu_load'] = sensor.Value
        
        # Memory Usage
        elif hardware.HardwareType == Hardware.HardwareType.Memory:
            for sensor in hardware.Sensors:
                if sensor.SensorType == Hardware.SensorType.Data and "Memory Used" in sensor.Name:
                    metrics['memory_used'] = sensor.Value
                elif sensor.SensorType == Hardware.SensorType.Data and "Memory Available" in sensor.Name:
                    metrics['memory_available'] = sensor.Value
                elif sensor.SensorType == Hardware.SensorType.Load and "Memory" in sensor.Name:
                    metrics['memory_load'] = sensor.Value
        
        # Storage Temperature
        elif hardware.HardwareType == Hardware.HardwareType.Storage:
            for sensor in hardware.Sensors:
                if sensor.SensorType == Hardware.SensorType.Temperature:
                    metrics['storage_temp'] = sensor.Value
    
    return metrics

# Usage
metrics = get_specific_metrics()
print(f"CPU Temperature: {metrics.get('cpu_temp', 'N/A')}°C")
print(f"CPU Load: {metrics.get('cpu_load', 'N/A')}%")
print(f"GPU Temperature: {metrics.get('gpu_temp', 'N/A')}°C")
print(f"Memory Usage: {metrics.get('memory_load', 'N/A')}%")