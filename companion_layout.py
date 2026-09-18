"""Window geometry for the three panels surrounding the real League client.

No Helper window occupies the client rectangle. Geometry is independent of Tk,
so monitor offsets, small work areas and overlap can be tested without a display.
"""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    def contains(self, other):
        return (self.x <= other.x and self.y <= other.y
                and self.right >= other.right and self.bottom >= other.bottom)

    def overlaps(self, other):
        return (self.x < other.right and other.x < self.right
                and self.y < other.bottom and other.y < self.bottom)


CLIENT_WIDTH, CLIENT_HEIGHT = 1280, 720
WING_WIDTH, DOCK_HEIGHT = 304, 300


def panel_layout(work, client, gap=0, min_wing=170, min_dock=240):
    """Fit a symmetric U-shaped frame to the client, never to the monitor width."""
    if client.width <= 0 or client.height < 300 or not work.contains(client):
        return None
    left = client.x - work.x - gap
    right = work.right - client.right - gap
    bottom = work.bottom - client.bottom - gap
    if min(left, right) < min_wing or bottom < min_dock:
        return None
    wing = min(left, right, WING_WIDTH)
    dock_left = client.x - gap - wing
    return {
        "allies": Rect(dock_left, client.y, wing, client.height),
        "enemies": Rect(client.right + gap, client.y, wing, client.height),
        "dock": Rect(dock_left, client.bottom + gap,
                     client.width + 2 * (wing + gap), min(bottom, DOCK_HEIGHT)),
    }


def suggested_client_rect(work):
    """Manual layout when League is closed; never resize the user's client."""
    margin = max(0, min(16, (work.height - CLIENT_HEIGHT - DOCK_HEIGHT) // 2))
    width = max(1, min(CLIENT_WIDTH, work.width - 2 * (WING_WIDTH + margin),
                       (work.height - DOCK_HEIGHT - 2 * margin) * 16 // 9))
    height = max(1, round(width * 9 / 16))
    return Rect(work.x + (work.width - width) // 2,
                work.y + max(margin, (work.height - height - DOCK_HEIGHT) // 2),
                width, height)


def snapshot_signature(snapshot):
    """Draft changes include bans and lane/local-player changes, not just picks."""
    teams = tuple(tuple((e.get("cellId"), e.get("championId"),
                         e.get("assignedPosition"), e.get("isLocalPlayer"),
                         e.get("pickTurn")) for e in snapshot.get(side, []))
                  for side in ("allies", "enemies"))
    bans = snapshot.get("bans") or {}
    return teams + (
        tuple(snapshot.get("allyBans", bans.get("myTeamBans", [])) or []),
        tuple(snapshot.get("enemyBans", bans.get("theirTeamBans", [])) or []),
        snapshot.get("phase"),
    )


class WindowsClient:
    """Read-only client discovery; SetWindowPos is used only on our Tk windows."""

    def __init__(self):
        self.available = os.name == "nt"
        if not self.available:
            return
        import ctypes as c
        from ctypes import wintypes as w
        self.c, self.w = c, w
        self.user = c.WinDLL("user32", use_last_error=True)
        self.kernel = c.WinDLL("kernel32", use_last_error=True)
        self.callback_type = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)
        declarations = {
            "EnumWindows": ([self.callback_type, w.LPARAM], w.BOOL),
            "IsWindowVisible": ([w.HWND], w.BOOL),
            "IsIconic": ([w.HWND], w.BOOL),
            "GetWindowTextW": ([w.HWND, w.LPWSTR, c.c_int], c.c_int),
            "GetWindowThreadProcessId": ([w.HWND, c.POINTER(w.DWORD)], w.DWORD),
            "GetWindowRect": ([w.HWND, c.POINTER(w.RECT)], w.BOOL),
            "GetClientRect": ([w.HWND, c.POINTER(w.RECT)], w.BOOL),
            "GetAncestor": ([w.HWND, w.UINT], w.HWND),
            "GetWindowLongW": ([w.HWND, c.c_int], w.LONG),
            "SetWindowLongW": ([w.HWND, c.c_int, w.LONG], w.LONG),
            "MonitorFromWindow": ([w.HWND, w.DWORD], w.HANDLE),
            "GetMonitorInfoW": ([w.HANDLE, c.c_void_p], w.BOOL),
            "SetWindowPos": ([w.HWND, w.HWND, c.c_int, c.c_int,
                              c.c_int, c.c_int, w.UINT], w.BOOL),
        }
        for name, (args, result) in declarations.items():
            fn = getattr(self.user, name)
            fn.argtypes, fn.restype = args, result
        self.kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        self.kernel.OpenProcess.restype = w.HANDLE
        self.kernel.CloseHandle.argtypes = [w.HANDLE]
        self.kernel.CloseHandle.restype = w.BOOL
        self.kernel.QueryFullProcessImageNameW.argtypes = [w.HANDLE, w.DWORD, w.LPWSTR, c.POINTER(w.DWORD)]
        self.kernel.QueryFullProcessImageNameW.restype = w.BOOL

    def _rect(self, value):
        return Rect(value.left, value.top, value.right - value.left, value.bottom - value.top)

    def work_area(self, hwnd):
        c, w = self.c, self.w
        class MonitorInfo(c.Structure):
            _fields_ = [("size", w.DWORD), ("monitor", w.RECT),
                        ("work", w.RECT), ("flags", w.DWORD)]
        info = MonitorInfo()
        info.size = c.sizeof(info)
        monitor = self.user.MonitorFromWindow(hwnd, 2)
        if self.user.GetMonitorInfoW(monitor, c.byref(info)):
            return self._rect(info.work)
        return None

    def find(self):
        if not self.available:
            return None
        c, w = self.c, self.w
        found = []

        @self.callback_type
        def visit(hwnd, _param):
            if not self.user.IsWindowVisible(hwnd) or self.user.IsIconic(hwnd):
                return True
            title = c.create_unicode_buffer(256)
            self.user.GetWindowTextW(hwnd, title, len(title))
            if "League of Legends" not in title.value:
                return True
            pid = w.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, c.byref(pid))
            process = self.kernel.OpenProcess(0x1000, False, pid.value)
            if not process:
                return True
            try:
                path = c.create_unicode_buffer(32768)
                size = w.DWORD(len(path))
                if not self.kernel.QueryFullProcessImageNameW(process, 0, path, c.byref(size)):
                    return True
                if os.path.basename(path.value).lower() != "leagueclientux.exe":
                    return True
                rect = w.RECT()
                if self.user.GetWindowRect(hwnd, c.byref(rect)):
                    work = self.work_area(hwnd)
                    if work:
                        found.append((work, self._rect(rect)))
            finally:
                self.kernel.CloseHandle(process)
            return not found

        self.user.EnumWindows(visit, 0)
        return found[0] if found else None

    def compact_chrome(self, window):
        """Remove only our dock's native frame, keeping its taskbar/minimize behavior."""
        if not self.available:
            return
        window.update_idletasks()
        hwnd = self.user.GetAncestor(window.winfo_id(), 2)
        style = self.user.GetWindowLongW(hwnd, -16)
        compact = style & ~0x00C40000  # WS_CAPTION | WS_THICKFRAME
        if style != compact:
            self.user.SetWindowLongW(hwnd, -16, compact)
            self.user.SetWindowPos(hwnd, None, 0, 0, 0, 0, 0x0037)

    def place(self, window, rect):
        """Account for native borders, and support negative monitor coordinates."""
        if not self.available:
            window.geometry(f"{rect.width}x{rect.height}+{max(0, rect.x)}+{max(0, rect.y)}")
            return
        window.update_idletasks()
        hwnd = self.user.GetAncestor(window.winfo_id(), 2)
        outer, inner = self.w.RECT(), self.w.RECT()
        border_w = border_h = 0
        if (self.user.GetWindowRect(hwnd, self.c.byref(outer))
                and self.user.GetClientRect(hwnd, self.c.byref(inner))):
            border_w = (outer.right - outer.left) - (inner.right - inner.left)
            border_h = (outer.bottom - outer.top) - (inner.bottom - inner.top)
        window.geometry(f"{max(1, rect.width-border_w)}x{max(1, rect.height-border_h)}")
        window.update_idletasks()
        # Do not raise/activate a helper panel over the League window.
        # Tk caches the removed caption dimensions on Windows. Set the outer
        # size as well so the dock and borderless wings meet at exact pixels.
        self.user.SetWindowPos(hwnd, None, rect.x, rect.y, rect.width, rect.height, 0x0014)


def enable_dpi_awareness():
    if os.name != "nt":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass  # Older Windows or a host which already set awareness.
