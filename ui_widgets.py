"""Small keyboard-accessible game buttons, drawn without extra dependencies."""
import tkinter as tk
from tkinter import font as tkfont


class GameButton(tk.Canvas):
    def __init__(self, parent, text, command=None, **options):
        self.skin = dict(text=text, command=command, bg='#122431', fg='#F0E6D2',
                         highlightbackground='#785A28', state='normal',
                         font='TkDefaultFont', padx=14, pady=8,
                         anchor='center', justify='center')
        self.skin.update(options)
        self.hover = self.pressed = False
        super().__init__(parent, bd=0, highlightthickness=0, takefocus=1,
                         background=parent.cget('background'), cursor='hand2')
        self._measure()
        self.bind('<Configure>', lambda _e: self._draw())
        self.bind('<Enter>', lambda _e: self._hover(True))
        self.bind('<Leave>', lambda _e: self._hover(False))
        self.bind('<ButtonPress-1>', self._press)
        self.bind('<ButtonRelease-1>', self._release)
        self.bind('<Return>', lambda _e: self.invoke())
        self.bind('<space>', lambda _e: self.invoke())
        self.bind('<FocusIn>', lambda _e: self._draw())
        self.bind('<FocusOut>', lambda _e: self._draw())

    def _measure(self):
        self.text_font = tkfont.Font(root=self, font=self.skin['font'])
        lines = str(self.skin['text']).split('\n')
        super().configure(width=max(self.text_font.measure(line) for line in lines) + 2*self.skin['padx'] + 4,
                          height=len(lines)*self.text_font.metrics('linespace') + 2*self.skin['pady'] + 4)

    def configure(self, cnf=None, **kwargs):
        changes = dict(cnf or {}, **kwargs)
        measured = any(k in changes for k in ('text', 'font', 'padx', 'pady'))
        self.skin.update(changes)
        if measured:
            self._measure()
        super().configure(takefocus=0 if self.skin['state'] == 'disabled' else 1)
        self._draw()

    config = configure

    def cget(self, key):
        return self.skin[key] if key in self.skin else super().cget(key)

    def invoke(self):
        if self.skin['state'] != 'disabled' and self.skin['command']:
            return self.skin['command']()

    def _hover(self, active):
        self.hover = active
        if not active:
            self.pressed = False
        self._draw()

    def _press(self, _event):
        if self.skin['state'] != 'disabled':
            self.focus_set()
            self.pressed = True
            self._draw()

    def _release(self, event):
        pressed, self.pressed = self.pressed, False
        self._draw()
        if pressed and 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height():
            self.invoke()

    def _draw(self):
        if not self.winfo_exists():
            return
        self.delete('all')
        w, h = self.winfo_width(), self.winfo_height()
        if w < 3 or h < 3:
            return
        enabled = self.skin['state'] != 'disabled'
        rgb = self.winfo_rgb(self.skin['bg'])
        base = [v//256 for v in rgb]
        for y in range(1, h-3):
            lift = (14 * (1-y/max(1, h-3)) + (9 if self.hover else 0)) if enabled else 0
            if self.pressed:
                lift = -7
            color = '#' + ''.join(f'{max(0, min(255, round(v+lift))):02x}' for v in base)
            self.create_line(2, y, w-3, y, fill=color)
        border = '#C8AA6E' if enabled and (self.hover or self.focus_get() is self) else self.skin['highlightbackground']
        self.create_rectangle(1, 1, w-2, h-4, outline=border)
        self.create_line(2, 2, w-3, 2, fill='#4A6269' if enabled and not self.pressed else '#071019')
        self.create_line(2, h-3, w-2, h-3, fill='#00050A', width=2)
        left = self.skin['anchor'] == 'w'
        self.create_text(self.skin['padx'] if left else w/2,
                         (h-3)/2 + int(self.pressed), anchor='w' if left else 'center',
                         text=self.skin['text'], font=self.text_font,
                         fill=self.skin['fg'] if enabled else '#74838B',
                         justify=self.skin['justify'], width=max(1, w-2*self.skin['padx']))
