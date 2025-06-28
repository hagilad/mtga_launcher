import ctypes
import subprocess
import time
from ctypes import wintypes
from typing import List, Tuple

import psutil
import win32api
import win32con
import win32gui
import win32process

from mtga_launcher import consts, exceptions


class MtgaLauncher:
    def __init__(self) -> None:
        self.mtga_launcher_process = subprocess.Popen(consts.MTGA_LAUNCHER_PATH)
        self.mtga_process_pid = self.wait_for_mtga_process()

        self.mtga_window = self.get_window_handle_by_pid(self.mtga_process_pid)
        self.resize_window(self.mtga_window)
        self.set_hook()

    def wait_for_mtga_process(self, timeout: int = 30) -> int:
        for _ in range(timeout * 2):
            for process in psutil.process_iter(["pid", "name"]):
                if process.info["name"] == consts.MTGA_EXECUTABLE:
                    return int(process.info["pid"])
            time.sleep(0.5)
        raise exceptions.MTGANotFoundException

    def get_window_handle_by_pid(self, pid: int, timeout: int = 10) -> int:
        for _ in range(timeout * 2):
            hwnds: List[int] = []

            def callback(hwnd: int, hwnds: List[int]) -> bool:
                if win32gui.IsWindowVisible(hwnd) and win32gui.IsWindowEnabled(hwnd):
                    _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if found_pid == pid:
                        hwnds.append(hwnd)
                return True

            win32gui.EnumWindows(callback, hwnds)

            for hwnd in hwnds:
                title = win32gui.GetWindowText(hwnd)
                if title.strip():  # Avoid blank title windows
                    print(f"🎯 Found window: {title} (HWND {hwnd})")
                    return hwnd

            time.sleep(0.5)

        raise exceptions.MTGANotFoundException("❌ Timed out waiting for MTGA window.")

    def resize_window(self, hwnd: int) -> None:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        style &= ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | win32con.WS_BORDER)
        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        width, height = self.get_window_screen_size(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetWindowPos(
            hwnd,
            win32con.HWND_TOP,
            0,
            0,
            width,
            height,
            win32con.SWP_FRAMECHANGED
            | win32con.SWP_NOZORDER
            | win32con.SWP_NOOWNERZORDER
            | win32con.SWP_SHOWWINDOW,
        )

    def get_window_screen_size(self, hwnd: int) -> Tuple[int, int]:
        monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)

        monitor_info = win32api.GetMonitorInfo(monitor)
        work_area = monitor_info["Monitor"]  # returns (left, top, right, bottom)

        width = work_area[2] - work_area[0]
        height = work_area[3] - work_area[1]

        return width, height

    def callback(
        self,
        hWinEventHook: wintypes.HANDLE,
        event: wintypes.DWORD,
        hwnd: int,
        idObject: wintypes.LONG,
        idChild: wintypes.LONG,
        dwEventThread: wintypes.DWORD,
        dwmsEventTime: wintypes.DWORD,
    ) -> None:
        if win32gui.IsWindowVisible(hwnd):
            if self.mtga_window == hwnd:
                x, y, r, b = win32gui.GetWindowRect(hwnd)
                desired_width, desired_height = self.get_window_screen_size(hwnd)
                w = r - x
                h = b - y
                if w != desired_width or h != desired_height:
                    self.resize_window(self.mtga_window)

    def set_hook(self) -> None:
        WinEventProc = consts.WinEventProcType(self.callback)
        user32 = ctypes.windll.user32
        hook = user32.SetWinEventHook(
            consts.EVENT_OBJECT_LOCATIONCHANGE,
            consts.EVENT_OBJECT_LOCATIONCHANGE,
            0,
            WinEventProc,
            0,
            0,
            consts.WINEVENT_OUTOFCONTEXT,
        )

        if not hook:
            raise exceptions.FailedToSetHook

        print("🛡️ Hook active — watching for MTGA window resizes.")
        msg = ctypes.wintypes.MSG()
        while psutil.pid_exists(self.mtga_process_pid):
            if user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 1):
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            time.sleep(0.1)
