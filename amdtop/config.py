"""Static paths, defaults, and display thresholds."""

from __future__ import annotations

# Refresh interval bounds (seconds).
DEFAULT_INTERVAL = 1.0
MIN_INTERVAL = 0.2
MAX_INTERVAL = 10.0

# sysfs locations. card1 is the Strix Halo iGPU; accel0 is the XDNA NPU.
DRM_DEVICE = "/sys/class/drm/card1/device"
GPU_METRICS = f"{DRM_DEVICE}/gpu_metrics"
GPU_BUSY = f"{DRM_DEVICE}/gpu_busy_percent"
VRAM_USED = f"{DRM_DEVICE}/mem_info_vram_used"
VRAM_TOTAL = f"{DRM_DEVICE}/mem_info_vram_total"
GTT_USED = f"{DRM_DEVICE}/mem_info_gtt_used"
GTT_TOTAL = f"{DRM_DEVICE}/mem_info_gtt_total"

NPU_DEVICE = "/sys/class/accel/accel0/device"

PROC_STAT = "/proc/stat"
CPUFREQ_GLOB = "/sys/devices/system/cpu/cpu[0-9]*/cpufreq/scaling_cur_freq"

# Color ramp for utilization gauges (percent breakpoints).
RAMP_GREEN_MAX = 60.0
RAMP_YELLOW_MAX = 85.0
