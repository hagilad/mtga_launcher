import ctypes
from ctypes import wintypes

MTGA_LAUNCHER_PATH = (
    r"C:\Program Files\Wizards of the Coast\MTGA\MTGALauncher\MTGALauncher.exe"
)
MTGA_EXECUTABLE = "MTGA.exe"
WINEVENT_OUTOFCONTEXT = 0x0000
EVENT_OBJECT_LOCATIONCHANGE = 0x800B
WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.HWND,
    wintypes.LONG,
    wintypes.LONG,
    wintypes.DWORD,
    wintypes.DWORD,
)
