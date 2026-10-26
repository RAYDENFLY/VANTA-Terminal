import os
import shutil
import ctypes
from typing import Dict, Any, Optional

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]

def get_system_memory() -> Dict[str, Any]:
    """Retrieves physical RAM telemetry on Windows using standard kernel32 call."""
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            total_gb = round(stat.ullTotalPhys / (1024 ** 3), 2)
            avail_gb = round(stat.ullAvailPhys / (1024 ** 3), 2)
            used_gb = round((stat.ullTotalPhys - stat.ullAvailPhys) / (1024 ** 3), 2)
            return {
                "total_ram_gb": total_gb,
                "available_ram_gb": avail_gb,
                "used_ram_gb": used_gb,
                "memory_load_percent": stat.dwMemoryLoad,
                "status": "warning" if avail_gb < 2.0 else "nominal"
            }
    except Exception:
        pass
    return {
        "total_ram_gb": None,
        "available_ram_gb": None,
        "used_ram_gb": None,
        "memory_load_percent": None,
        "status": "unavailable"
    }

def get_disk_usage(path: str = "D:\\") -> Dict[str, Any]:
    """Retrieves disk usage using standard shutil library."""
    try:
        total, used, free = shutil.disk_usage(path)
        return {
            "drive": path[:2],
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "percent_free": round((free / total) * 100, 1),
            "status": "nominal" if (free / (1024 ** 3)) > 10.0 else "low_space"
        }
    except Exception:
        return {
            "drive": path[:2],
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "percent_free": None,
            "status": "unavailable"
        }

def get_cpu_info() -> Dict[str, Any]:
    """Retrieves basic CPU metadata."""
    try:
        cores = os.cpu_count() or 4
        return {
            "logical_cores": cores,
            "physical_cores": max(1, cores // 2),
            "architecture": os.environ.get("PROCESSOR_ARCHITECTURE", "x64"),
            "processor_identifier": os.environ.get("PROCESSOR_IDENTIFIER", "Intel64"),
        }
    except Exception:
        return {
            "logical_cores": 4,
            "physical_cores": 2,
            "architecture": "x64",
            "processor_identifier": "unavailable"
        }

def get_all_resource_telemetry() -> Dict[str, Any]:
    return {
        "memory": get_system_memory(),
        "disk_d": get_disk_usage("D:\\"),
        "disk_c": get_disk_usage("C:\\"),
        "cpu": get_cpu_info(),
        "worker_concurrency_cap": 1
    }
