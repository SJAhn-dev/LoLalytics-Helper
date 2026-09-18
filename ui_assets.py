"""Bundled, offline portraits and process-private Pretendard fonts."""
import base64
import ctypes
import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import font
import zipfile
from common import resolve_resource_path


class UIAssets:
    def __init__(self, root):
        self.root, self.images, self.font_files = root, {}, []
        self.archive = None
        self.directory = None
        try:
            self.archive = zipfile.ZipFile(resolve_resource_path('ui_assets.zip'))
            if os.name == 'nt':
                self.directory = tempfile.TemporaryDirectory(prefix='lolalytics-fonts-')
                add = ctypes.windll.gdi32.AddFontResourceExW
                add.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
                add.restype = ctypes.c_int
                for name in ('Pretendard-Regular.otf', 'Pretendard-Bold.otf'):
                    path = Path(self.directory.name) / name
                    path.write_bytes(self.archive.read('fonts/' + name))
                    if add(str(path), 0x10, None):
                        self.font_files.append(path)
        except (OSError, KeyError, zipfile.BadZipFile):
            pass
        families = set(font.families(root))
        self.family = next((f for f in ('Pretendard', 'Segoe UI', 'Malgun Gothic')
                            if f in families), 'TkDefaultFont')
        for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
            font.nametofont(name, root=root).configure(family=self.family, size=-13)
        # The League rectangle is measured in physical pixels. Pixel-sized
        # fonts keep five information cards legible within its 720px height.
        root.option_add('*Font', (self.family, -13))

    def portrait(self, canonical, size=40):
        key = (canonical, size)
        if key not in self.images:
            try:
                raw = self.archive.read(f'portraits/{canonical}.png')
                original = tk.PhotoImage(master=self.root, data=base64.b64encode(raw))
                self.images[key] = original.subsample(max(1, original.width() // size))
            except (AttributeError, KeyError, tk.TclError, OSError):
                self.images[key] = None
        return self.images[key]

    def close(self):
        self.images.clear()
        if os.name == 'nt':
            remove = ctypes.windll.gdi32.RemoveFontResourceExW
            remove.argtypes = [ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
            for path in self.font_files:
                remove(str(path), 0x10, None)
        if self.archive:
            self.archive.close()
        if self.directory:
            self.directory.cleanup()
