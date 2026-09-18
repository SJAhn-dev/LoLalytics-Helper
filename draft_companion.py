"""Hextech draft UI: two team wings and a recommendation dock.

The application owns only these three windows. The centre is the user's real
League client, not an imitation or an input-blocking transparent overlay.
"""
import tkinter as tk
from tkinter import ttk

from common import LANES, AutocompletePopup, ScoreTooltip
from companion_layout import Rect, WindowsClient, panel_layout, suggested_client_rect

VOID = "#010A13"
PANEL = "#071521"
GOLD = "#C8AA6E"
METAL = "#785A28"
TEXT = "#F0E6D2"
MUTED = "#A09B8C"
CYAN = "#0AC8B9"
SELECT = "#12313B"
LANE_NAMES = dict(zip(LANES, ("탑", "정글", "미드", "바텀", "서포터")))

HEXTECH_THEME = {
    "name": "hextech", "bg_color": VOID, "fg_color": TEXT,
    "accent_color": PANEL, "select_color": SELECT,
    "button_color": PANEL, "button_fg": GOLD,
    "button_active_bg": SELECT, "button_pressed_bg": "#0A242E",
    "entry_bg": "#0A1428", "entry_fg": TEXT,
    "treeview_bg": VOID, "treeview_heading_bg": PANEL,
    "low_sample": "#D7A86E", "normal_sample": TEXT,
    "tooltip_bg": PANEL, "tooltip_fg": TEXT,
    "score_default": GOLD, "score_high": CYAN,
    "score_medium": GOLD, "score_low": "#D78076",
}


def button(parent, text, command, **kwargs):
    return tk.Button(parent, text=text, command=command, bg=PANEL, fg=GOLD,
                     activebackground=SELECT, activeforeground=TEXT,
                     relief="flat", bd=0, highlightthickness=1,
                     highlightbackground=METAL, padx=10, pady=4, **kwargs)


def create_team_column(app, parent, title, side):
    column = tk.Frame(parent, bg=VOID, highlightthickness=1, highlightbackground=METAL)
    heading = tk.Label(column, text=title, bg=PANEL, fg=GOLD,
                       font=("Malgun Gothic", 12, "bold"), anchor="w", padx=12, pady=10)
    heading.pack(fill="x")
    basis = tk.Label(column, text="하단에서 추천 후보를 선택하세요", bg=VOID,
                     fg=MUTED, font=("Malgun Gothic", 8), anchor="w", padx=10, pady=7)
    basis.pack(fill="x")
    app.draft_dashboard.basis_labels[side] = basis
    app.draft_dashboard.make_draggable(heading, parent)

    scroll_area = tk.Frame(column, bg=VOID)
    scroll_area.pack(fill="both", expand=True)
    canvas = tk.Canvas(scroll_area, bg=VOID, bd=0, highlightthickness=0, width=170)
    scrollbar = ttk.Scrollbar(scroll_area, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    roster = tk.Frame(canvas, bg=VOID)
    item = canvas.create_window((0, 0), anchor="nw", window=roster)
    roster.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.bind("<Configure>", lambda e: canvas.itemconfigure(item, width=e.width))

    for idx, lane in enumerate(LANES):
        row = tk.Frame(roster, bg=PANEL, highlightthickness=1, highlightbackground="#253139")
        row.pack(fill="x", padx=5, pady=3)
        summary = tk.Frame(row, bg=PANEL)
        summary.pack(fill="x", padx=6, pady=5)
        summary.columnconfigure(0, weight=1)
        name_var = tk.StringVar(value="선택 대기")
        name = tk.Button(summary, textvariable=name_var, anchor="w", relief="flat",
                         bg=PANEL, fg=TEXT, activebackground=SELECT,
                         activeforeground=TEXT, font=("Malgun Gothic", 10, "bold"),
                         bd=0, padx=0, pady=0)
        name.grid(row=0, column=0, sticky="ew")
        relation_var = tk.StringVar(value="—")
        tk.Label(summary, textvariable=relation_var, bg=PANEL, fg=CYAN,
                 font=("Segoe UI", 10)).grid(row=0, column=1, rowspan=2, padx=(3, 0))
        lane_var = tk.StringVar(value=LANE_NAMES[lane])
        tk.Label(summary, textvariable=lane_var, bg=PANEL, fg=MUTED,
                 font=("Malgun Gothic", 8), anchor="w").grid(row=1, column=0, sticky="w")

        editor = tk.Frame(row, bg=PANEL, padx=6, pady=5)
        editor.columnconfigure(0, weight=1)
        entry = tk.Entry(editor, width=10)
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        lane_box = ttk.Combobox(editor, values=LANES, state="readonly", width=8)
        lane_box.set(lane)
        lane_box.grid(row=0, column=1, sticky="e")
        actions = tk.Frame(editor, bg=PANEL)
        actions.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        search = button(actions, "적용", None)
        search.pack(side="left")
        clear = button(actions, "비우기", None)
        clear.pack(side="left", padx=4)
        options = tk.Frame(editor, bg=PANEL)
        options.grid(row=2, column=0, columnspan=2, sticky="w")
        manual = tk.BooleanVar(value=False)
        exclude = tk.BooleanVar(value=False)
        tk.Checkbutton(options, text="라인 고정", variable=manual, bg=PANEL,
                       fg=TEXT, selectcolor=VOID, activebackground=PANEL).pack(anchor="w")
        tk.Checkbutton(options, text="분석 제외", variable=exclude, bg=PANEL,
                       fg=TEXT, selectcolor=VOID, activebackground=PANEL).pack(anchor="w")
        result = tk.StringVar(value="챔피언을 선택하세요")
        result_label = tk.Label(editor, textvariable=result, bg=PANEL, fg=MUTED,
                                anchor="w", font=("Malgun Gothic", 8), wraplength=210)
        result_label.grid(row=3, column=0, columnspan=2, sticky="ew")
        slot = dict(side=side, index=idx, entry=entry, lane=lane_box, button=search,
                    clear_button=clear, result_var=result, result_label=result_label,
                    exclude_var=exclude, manual_var=manual, display_name=None,
                    canonical_name=None, selected_lane=None, synergy_dataset=None,
                    counter_dataset=None, last_lane_value=None, last_lane=None,
                    score_details=None, name_var=name_var, lane_var=lane_var,
                    relation_var=relation_var, frame=row, editor=editor)

        def toggle(s=slot):
            if s["editor"].winfo_manager():
                s["editor"].pack_forget()
            else:
                s["editor"].pack(fill="x")
                if not s["entry"].get() and s.get("display_name"):
                    s["entry"].insert(0, s["display_name"])
                s["entry"].focus_set()
        name.configure(command=toggle)
        search.configure(command=lambda s=slot: app.perform_banpick_search(s))
        clear.configure(command=lambda s=slot: app.clear_banpick_slot(s))
        entry.bind("<Return>", lambda _e, s=slot: app.perform_banpick_search(s))
        entry.bind("<Escape>", lambda _e, s=slot: s["editor"].pack_forget())
        lane_box.bind("<<ComboboxSelected>>", lambda _e, s=slot: app.on_banpick_lane_changed(s))
        exclude.trace_add("write", lambda *_: app.update_banpick_recommendations())
        manual.trace_add("write", lambda *_: app.draft_dashboard.refresh_slots())
        slot["autocomplete"] = AutocompletePopup(entry, app.get_autocomplete_candidates,
            display_formatter=app.format_display_name,
            on_select=lambda _value, s=slot: app.perform_banpick_search(s))
        slot["tooltip"] = ScoreTooltip(result_label, lambda s=slot: app._get_score_tooltip_text(s))
        app._update_slot_lane_cache(slot)
        app.banpick_slots[side].append(slot)

    ban = tk.Label(column, text="밴: —", anchor="w", bg=VOID, fg=MUTED,
                   padx=10, pady=7, wraplength=220)
    ban.pack(fill="x")
    total = tk.Label(column, text="조합 점수: —", bg=VOID, fg=GOLD, anchor="w", padx=10, pady=5)
    total.pack(fill="x")
    return column, total, ban


class DraftCompanion:
    def __init__(self, app):
        self.app, self.root = app, app.root
        self.native = WindowsClient()
        self.windows, self.basis_labels = {}, {}
        self.records, self.selected_name = {}, None
        self.cards = []
        self.closed = False
        self.job = None
        self.last_geometry = None
        self.follow = tk.BooleanVar(value=app.ui_settings.get("client_follow", True))
        self.layout_status = tk.StringVar(value="중앙은 실제 LoL 클라이언트 자리입니다")
        self.detail = tk.StringVar(value="내 라인을 선택하고 조합을 입력하세요")
        self.app.draft_dashboard = self
        self._build()
        self.root.after_idle(self.arrange_default)
        self.job = self.root.after(800, self._tick)
        self.app.notebook.bind("<<NotebookTabChanged>>", lambda _e: self._visibility(), add="+")
        self.root.bind("<Destroy>", self._destroyed, add="+")
        self.root.bind("<FocusIn>", self._raise_wings, add="+")

    def _raise_wings(self, event):
        if event.widget is self.root and self._active():
            for window in self.windows.values():
                if window.state() != "withdrawn":
                    window.lift()

    def _build(self):
        app, frame = self.app, self.app.dashboard_tab
        frame.configure(bg=VOID)
        app.banpick_slots = {"allies": [], "enemies": []}
        app.my_lane_var = tk.StringVar(value="")
        app.active_slot_var = tk.StringVar(value="")  # legacy lane-swap compatibility
        app.my_lane_var.trace_add("write", lambda *_: app.update_banpick_recommendations())

        top = tk.Frame(frame, bg=VOID)
        top.pack(fill="x", padx=12, pady=(6, 3))
        tk.Label(top, text="LoLALYTICS  /  DRAFT COMPANION", fg=GOLD, bg=VOID,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(top, textvariable=app.lcu_status_var, fg=MUTED, bg=VOID).pack(side="left", padx=15)
        app.lcu_check_button = button(top, "연결", app.on_lcu_check_clicked,
                                      state="normal" if app.client_sync_supported else "disabled")
        app.lcu_check_button.pack(side="right")
        app.client_sync_checkbox = tk.Checkbutton(top, text="자동 동기화", variable=app.client_sync_var,
            command=app.on_client_sync_toggle, state="disabled", bg=VOID, fg=MUTED, selectcolor=PANEL)
        app.client_sync_checkbox.pack(side="right", padx=8)

        tools = tk.Frame(frame, bg=VOID)
        tools.pack(fill="x", padx=12, pady=3)
        tk.Label(tools, text="내 라인", bg=VOID, fg=MUTED).pack(side="left", padx=(0, 8))
        for lane, label in LANE_NAMES.items():
            tk.Radiobutton(tools, text=label, variable=app.my_lane_var, value=lane,
                           indicatoron=False, bg=PANEL, fg=TEXT, selectcolor=SELECT,
                           activebackground=SELECT, relief="flat", width=5,
                           borderwidth=0, padx=4, pady=4).pack(side="left", padx=2)
        button(tools, "전체 순위 / 필터", self.toggle_list).pack(side="left", padx=10)
        button(tools, "기본 배치", self.arrange_default).pack(side="right")
        tk.Checkbutton(tools, text="클라이언트 따라가기", variable=self.follow,
                       command=self._follow_changed, bg=VOID, fg=MUTED,
                       selectcolor=PANEL).pack(side="right", padx=6)
        more = tk.Menubutton(tools, text="더 보기 ▾", bg=PANEL, fg=GOLD, relief="flat", padx=8)
        menu = tk.Menu(more, tearoff=False, bg=PANEL, fg=TEXT)
        menu.add_command(label="수동 불러오기", command=app.manual_client_import)
        menu.add_command(label="스냅샷 불러오기", command=app.load_snapshot)
        menu.add_command(label="스냅샷 저장", command=app.save_snapshot)
        menu.add_command(label="선택 챔피언 제외", command=app.ignore_selected_recommendations)
        menu.add_command(label="조합 초기화", command=app.reset_dashboard_tab)
        more.configure(menu=menu)
        more.pack(side="right", padx=5)
        # The existing connection handler enables this control after an LCU check.
        menu.entryconfigure(0, state="disabled")
        class FetchAction:
            def config(self, **options):
                menu.entryconfigure(0, **options)
        app.client_fetch_button = FetchAction()

        self.card_frame = tk.Frame(frame, bg=VOID)
        self.card_frame.pack(fill="both", expand=True, padx=12, pady=5)
        for idx in range(3):
            self.card_frame.columnconfigure(idx, weight=1, uniform="candidates")
            card = button(self.card_frame, f"{idx+1:02d}   추천 대기", lambda i=idx: self.select_card(i),
                          anchor="w", justify="left", font=("Malgun Gothic", 11))
            card.grid(row=0, column=idx, sticky="nsew", padx=(0, 8 if idx < 2 else 0), ipady=8)
            self.cards.append(card)
        self.card_frame.rowconfigure(0, weight=1)

        self.list_frame = tk.Frame(frame, bg=VOID)
        filters = tk.Frame(self.list_frame, bg=VOID)
        filters.pack(fill="x")
        tk.Label(filters, text="최소 게임 수", bg=VOID, fg=MUTED).pack(side="left")
        app.recommend_min_games_entry = tk.Entry(filters, width=7)
        app.recommend_min_games_entry.insert(0, "900")
        app.recommend_min_games_entry.pack(side="left", padx=5)
        tk.Label(filters, text="또는 픽률(%)", bg=VOID, fg=MUTED).pack(side="left")
        app.recommend_pick_rate_entry = tk.Entry(filters, width=6)
        app.recommend_pick_rate_entry.insert(0, "1.5")
        app.recommend_pick_rate_entry.pack(side="left", padx=5)
        for entry in (app.recommend_min_games_entry, app.recommend_pick_rate_entry):
            entry.bind("<Return>", lambda _e: app.update_banpick_recommendations())
            entry.bind("<FocusOut>", lambda _e: app.update_banpick_recommendations())
        button(filters, "적용", app.update_banpick_recommendations).pack(side="left")
        columns = ("챔피언", "태그", "최종 점수", "시너지", "카운터")
        table = tk.Frame(self.list_frame, bg=VOID)
        table.pack(fill="both", expand=True, pady=4)
        app.recommend_tree = ttk.Treeview(table, columns=columns, show="headings", height=4)
        for col, width in zip(columns, (130, 170, 90, 420, 420)):
            app.recommend_tree.heading(col, text="추천 점수" if col == "최종 점수" else col)
            app.recommend_tree.column(col, width=width, minwidth=70, anchor="w")
        vertical = ttk.Scrollbar(table, orient="vertical", command=app.recommend_tree.yview)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=app.recommend_tree.xview)
        app.recommend_tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        vertical.pack(side="right", fill="y")
        horizontal.pack(side="bottom", fill="x")
        app.recommend_tree.pack(fill="both", expand=True)
        app.recommend_tree.bind("<<TreeviewSelect>>", self._select_tree)

        footer = tk.Frame(frame, bg=VOID)
        footer.pack(fill="x", padx=12, pady=(2, 6))
        self.footer = footer
        tk.Label(footer, textvariable=self.detail, bg=VOID, fg=GOLD, anchor="w").pack(fill="x")
        tk.Label(footer, textvariable=self.layout_status, bg=VOID, fg=MUTED,
                 anchor="w", font=("Malgun Gothic", 8)).pack(fill="x")
        app.team_total_labels, app.ban_labels = {}, {}
        for side, title in (("allies", "우리 팀  /  시너지"), ("enemies", "상대 팀  /  상성")):
            window = tk.Toplevel(self.root)
            window.withdraw()
            window.title(f"LoLalytics Helper — {title}")
            window.overrideredirect(True)
            window.transient(self.root)
            window.configure(bg=VOID)
            self.windows[side] = window
            column, total, ban = create_team_column(app, window, title, side)
            column.pack(fill="both", expand=True)
            app.team_total_labels[side], app.ban_labels[side] = total, ban

    def toggle_list(self):
        if self.list_frame.winfo_manager():
            self.list_frame.pack_forget()
            self.card_frame.pack(fill="both", expand=True, padx=12, pady=5, before=self.footer)
        else:
            self.card_frame.pack_forget()
            self.list_frame.pack(fill="both", expand=True, padx=12, pady=5, before=self.footer)

    def _follow_changed(self):
        self.app.ui_settings["client_follow"] = self.follow.get()
        self.app._save_ui_settings()
        self.last_geometry = None

    def make_draggable(self, heading, window):
        origin = {}
        def start(event):
            origin.update(x=event.x_root, y=event.y_root,
                          wx=window.winfo_x(), wy=window.winfo_y())
        def drag(event):
            if not origin:
                return
            self.follow.set(False)
            self.layout_status.set("수동 배치 · 패널 제목을 끌어 이동할 수 있습니다")
            self.native.place(window, Rect(origin["wx"]+event.x_root-origin["x"],
                origin["wy"]+event.y_root-origin["y"], window.winfo_width(), window.winfo_height()))
        heading.bind("<ButtonPress-1>", start)
        heading.bind("<B1-Motion>", drag)

    def _active(self):
        return (self.root.state() not in ("withdrawn", "iconic")
                and self.app.notebook.select() == str(self.app.dashboard_tab))

    def _visibility(self, show=None):
        visible = self._active() if show is None else (show and self._active())
        for window in self.windows.values():
            if visible:
                if window.state() == "withdrawn":
                    window.deiconify()
                    window.lift()
            else:
                window.withdraw()

    def _place_layout(self, layout):
        for side, window in self.windows.items():
            self.native.place(window, layout[side])
        self.native.place(self.root, layout["dock"])
        self.last_geometry = layout
        self._visibility()

    def arrange_default(self):
        if self.closed or not self._active():
            return
        work = None
        if self.native.available:
            work = self.native.work_area(self.native.user.GetAncestor(self.root.winfo_id(), 2))
        work = work or Rect(0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()-40)
        found = self.native.find() if self.follow.get() else None
        layout = panel_layout(*found) if found else panel_layout(work, suggested_client_rect(work))
        if layout:
            self._place_layout(layout)
            self.layout_status.set("중앙은 실제 LoL 클라이언트 자리 · 제목을 끌어 수동 배치 · 추천 점수 ≠ 승률")
        else:
            self._visibility(False)
            self.layout_status.set("클라이언트 양옆 170px·아래 250px 이상 공간을 확보한 후 기본 배치를 누르세요")

    def _tick(self):
        if self.closed:
            return
        try:
            visible = self._active()
            if visible and self.follow.get():
                found = self.native.find()
                if found:
                    layout = panel_layout(*found)
                    if layout:
                        if layout != self.last_geometry:
                            self._place_layout(layout)
                        self.layout_status.set("클라이언트 옆에 배치됨 · 추천 점수 ≠ 승률")
                    else:
                        visible = False
                        self.layout_status.set("배치 공간 부족 · 클라이언트를 줄이거나 이동한 후 다시 배치하세요")
            self._visibility(visible)
            self.job = self.root.after(800, self._tick)
        except tk.TclError:
            self.closed = True

    def _destroyed(self, event):
        if event.widget is self.root:
            self.closed = True
            if self.job:
                try:
                    self.root.after_cancel(self.job)
                except tk.TclError:
                    pass

    def refresh_slots(self):
        my_lane = self.app.my_lane_var.get()
        for side, slots in self.app.banpick_slots.items():
            for slot in slots:
                if "name_var" not in slot:
                    continue
                lane = slot["lane"].get()
                is_me = side == "allies" and lane == my_lane
                slot["name_var"].set(slot.get("display_name") or "선택 대기")
                suffix = " · 내 라인" if is_me else ""
                if slot["manual_var"].get():
                    suffix += " · 라인 고정"
                if slot["exclude_var"].get():
                    suffix += " · 제외"
                slot["lane_var"].set(LANE_NAMES.get(lane, lane) + suffix)
                slot["frame"].configure(highlightbackground=CYAN if is_me else "#253139")

    def set_recommendations(self, recommendations, components=None):
        self.refresh_slots()
        components = components or {}
        self.records = {row[0]: (row, components.get(row[0], {})) for row in recommendations[:20]}
        self.card_names = list(self.records)[:3]
        if self.selected_name not in self.records:
            self.selected_name = next(iter(self.records), None)
        for idx, card in enumerate(self.cards):
            if idx >= len(self.card_names):
                card.configure(text=f"{idx+1:02d}   후보 없음", state="disabled", bg=PANEL)
                continue
            name = self.card_names[idx]
            row, data = self.records[name]
            missing = data.get("missing_relations", 0)
            reason = f"관계 {missing}개 자료 없음" if missing else (" · ".join(row[7]) or "조합 근거 확인")
            card.configure(text=f"{idx+1:02d}   {self.app.format_display_name(name)}     {row[1]:.2f}\n{reason}", state="normal")
        self._show_selected()

    def select_card(self, index):
        if index < len(getattr(self, "card_names", [])):
            self.selected_name = self.card_names[index]
            self._show_selected()

    def _select_tree(self, _event):
        selected = self.app.recommend_tree.selection()
        if selected:
            name = self._tree_record_name(selected[0])
            if name in self.records:
                self.selected_name = name
                self._show_selected()

    def _tree_record_name(self, item):
        if item in self.records:
            return item
        label = self.app.recommend_tree.item(item, "values")[0].removeprefix("⚠ ")
        return next((name for name in self.records
                     if self.app.format_display_name(name) == label), None)

    def _show_selected(self):
        for idx, name in enumerate(getattr(self, "card_names", [])):
            active = name == self.selected_name
            self.cards[idx].configure(bg=SELECT if active else PANEL,
                                      highlightbackground=GOLD if active else METAL)
        data = self.records.get(self.selected_name)
        if not data:
            self.detail.set("내 라인과 조합을 입력하세요 · 조건에 맞는 추천이 없습니다")
        else:
            row, values = data
            self.detail.set(f"{self.app.format_display_name(row[0])}  |  시너지 {row[2]:.2f}  ·  상성 {row[3]:.2f}  |  "
                            f"확인된 관계 {values.get('known_relations', 0)} / {values.get('expected_relations', 0)}")
            tree = self.app.recommend_tree
            for item in tree.get_children():
                name = self._tree_record_name(item)
                if name == self.selected_name:
                    if tree.selection() != (item,):
                        tree.selection_set(item)
                    break
        for side, field in (("allies", "synergy_relations"), ("enemies", "counter_relations")):
            self.basis_labels[side].configure(text=(f"{self.app.format_display_name(self.selected_name)} 기준 관계별 승률" if data else "하단에서 추천 후보를 선택하세요"))
            relations = data[1].get(field, {}) if data else {}
            for slot in self.app.banpick_slots[side]:
                relation = relations.get(slot["index"])
                active = slot.get("canonical_name") and not slot["exclude_var"].get()
                own = side == "allies" and slot["lane"].get() == self.app.my_lane_var.get()
                text = f"{relation['win_rate']:.1f}%" if relation else ("자료 없음" if data and active and not own else "—")
                slot["relation_var"].set(text)
