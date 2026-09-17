"""Regression checks for docking, candidate evidence and GUI lifecycle."""
import copy
import os
import threading
from unittest.mock import Mock

import pytest

from companion_layout import Rect, panel_layout, snapshot_signature, suggested_client_rect
from lobby_manager import ChampionScraperApp


@pytest.mark.parametrize("work", [Rect(0, 0, 1920, 1040), Rect(-1920, 0, 1920, 1040),
                                     Rect(1920, -200, 2560, 1400), Rect(0, 0, 1366, 728)])
def test_panels_stay_inside_work_area_and_outside_client(work):
    client = suggested_client_rect(work)
    layout = panel_layout(work, client)
    assert layout is not None
    for panel in layout.values():
        assert work.contains(panel)
        assert not panel.overlaps(client)
    panels = list(layout.values())
    assert all(not a.overlaps(b) for i, a in enumerate(panels) for b in panels[i+1:])


@pytest.mark.parametrize("client", [Rect(0, 0, 1920, 1040), Rect(320, 320, 1280, 720),
                                      Rect(-10, 20, 1200, 700), Rect(10, 20, 1280, 720)])
def test_unsafe_layouts_are_rejected(client):
    assert panel_layout(Rect(0, 0, 1920, 1040), client) is None


def test_bans_and_lane_changes_invalidate_signature():
    snapshot = {"allies": [{"championId": 1, "assignedPosition": "top"}],
                "enemies": [], "allyBans": [], "enemyBans": []}
    first = snapshot_signature(snapshot)
    snapshot["enemyBans"] = [103]
    assert snapshot_signature(snapshot) != first
    second = snapshot_signature(snapshot)
    snapshot["allies"][0]["assignedPosition"] = "middle"
    assert snapshot_signature(snapshot) != second


def value(v):
    return Mock(get=Mock(return_value=v))


def slot(name, lane, **kwargs):
    return dict(canonical_name=name, display_name=name, selected_lane=lane,
                lane=value(lane), exclude_var=value(False), **kwargs)


def recommendation_app():
    app = ChampionScraperApp.__new__(ChampionScraperApp)
    app.my_lane_var = value("middle")
    app.banpick_slots = {"allies": [slot(None, "middle")], "enemies": []}
    app.recommend_tree = Mock()
    app.recommend_tree.get_children.return_value = []
    app.recommend_min_games_entry = value("900")
    app.recommend_pick_rate_entry = value("1.5")
    app.champion_data_cache = {}
    app.resolve_champion_name = lambda name: name
    app.get_lane_weight = lambda *_: 1
    app.is_champion_banned = lambda _: False
    app.is_champion_ignored = lambda _: False
    app._check_champion_data_exists = lambda *_: True
    app._qualifies_for_pre_pick_tag = lambda *_: False
    app.update_team_total_scores = Mock()
    app._update_all_slot_scores = Mock()
    app.draft_dashboard = Mock()
    return app


def test_candidate_evidence_is_inverted_to_candidate_perspective_and_tracks_missing():
    app = recommendation_app()
    app.banpick_slots["enemies"] = [
        slot("Ahri", "middle", counter_dataset={"middle": {
            "Orianna": {"win_rate": "47.5", "games": 12000, "pick_rate": 3}}}),
        slot("Garen", "top", counter_dataset={}),
    ]
    app.update_banpick_recommendations()
    recommendations, components = app.draft_dashboard.set_recommendations.call_args.args
    assert recommendations[0][1] == 52.5
    evidence = components["Orianna"]
    assert evidence["counter_relations"][0] == {"win_rate": 52.5, "games": 12000}
    assert evidence["known_relations"] == 1
    assert evidence["expected_relations"] == 2
    assert evidence["missing_relations"] == 1
    assert "신뢰도 높음" not in evidence["tags"]
    assert "올카운터" not in evidence["tags"]


def test_my_slot_is_not_counted_as_a_synergy_partner():
    app = recommendation_app()
    app.banpick_slots["allies"][0].update(canonical_name="Ahri", display_name="Ahri",
        synergy_dataset={"middle": {"Orianna": {"win_rate": 80, "games": 12000}}})
    app.banpick_slots["allies"].append(slot("Jarvan", "jungle", synergy_dataset={"middle": {
        "Orianna": {"win_rate": 54, "games": 12000}}}))
    app.update_banpick_recommendations()
    rows, evidence = app.draft_dashboard.set_recommendations.call_args.args
    assert rows[0][1] == 54
    assert evidence["Orianna"]["expected_relations"] == 1


def test_ban_only_snapshot_recomputes_recommendations():
    app = ChampionScraperApp.__new__(ChampionScraperApp)
    app.banned_champions = set()
    app._normalize_client_entries = lambda entries: entries
    app._populate_side_from_client = Mock(return_value=False)
    app._update_banned_champions_from_snapshot = lambda _: app.banned_champions.add("ahri")
    app.update_banpick_recommendations = Mock()
    assert app._apply_client_snapshot({"allies": [], "enemies": [], "enemyBans": [103]})
    app.update_banpick_recommendations.assert_called_once()


@pytest.fixture
def gui_app(monkeypatch):
    import tkinter as tk
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        if os.environ.get("REQUIRE_TK") == "1":
            pytest.fail(f"Tk is required for this run: {exc}")
        pytest.skip(f"Tk runtime unavailable: {exc}")
    root.withdraw()
    monkeypatch.setattr(ChampionScraperApp, "_save_ui_settings", lambda self: None)
    app = ChampionScraperApp(root)
    yield app
    app.close()


def test_gui_builds_synchronously_on_main_thread(gui_app):
    assert threading.current_thread() is threading.main_thread()
    assert len(gui_app.banpick_slots["allies"]) == 5
    assert len(gui_app.banpick_slots["enemies"]) == 5
    assert len(gui_app.draft_dashboard.windows) == 2
    assert gui_app.root.state() == "withdrawn"
    gui_app.root.update()
    assert all(w.state() == "withdrawn" for w in gui_app.draft_dashboard.windows.values())


def test_candidate_selection_updates_both_wings_and_survives_refresh(gui_app):
    ui = gui_app.draft_dashboard
    records = [("오리아나", 104.2, 52.8, 51.4, [], [], False, []),
               ("신드라", 103.1, 50.7, 52.4, [], [], False, [])]
    evidence = {"오리아나": {"synergy_relations": {0: {"win_rate": 54.1}},
                            "counter_relations": {0: {"win_rate": 51.6}}},
                "신드라": {"synergy_relations": {0: {"win_rate": 51.8}},
                          "counter_relations": {0: {"win_rate": 53.2}}}}
    ui.set_recommendations(records, evidence)
    ui.cards[1].invoke()
    assert gui_app.banpick_slots["allies"][0]["relation_var"].get() == "51.8%"
    assert gui_app.banpick_slots["enemies"][0]["relation_var"].get() == "53.2%"
    ui.set_recommendations(list(reversed(records)), copy.deepcopy(evidence))
    assert ui.selected_name == "신드라"
    ui.set_recommendations([])
    assert ui.selected_name is None
    assert gui_app.banpick_slots["allies"][0]["relation_var"].get() == "—"


def test_full_list_toggle_and_slot_editor(gui_app):
    ui = gui_app.draft_dashboard
    ui.toggle_list()
    assert ui.list_frame.winfo_manager() == "pack"
    assert not ui.card_frame.winfo_manager()
    ui.toggle_list()
    assert ui.card_frame.winfo_manager() == "pack"
    assert not ui.list_frame.winfo_manager()


def test_connection_status_and_candidate_exclusion_target(gui_app):
    gui_app._set_client_status("미연결 · 수동 입력")
    assert gui_app.lcu_status_var.get() == "미연결 · 수동 입력"
    ui = gui_app.draft_dashboard
    tree = gui_app.recommend_tree
    first = tree.insert("", "end", values=("오리아나", "", "104.2", "", ""))
    second = tree.insert("", "end", values=("신드라", "", "103.1", "", ""))
    rows = [("오리아나", 104.2, 52.8, 51.4, [], [], False, []),
            ("신드라", 103.1, 50.7, 52.4, [], [], False, [])]
    ui.set_recommendations(rows)
    assert tree.selection() == (first,)
    ui.cards[1].invoke()
    assert tree.selection() == (second,)
    gui_app.client_fetch_button.config(state="disabled")
    gui_app.client_fetch_button.config(state="normal")
