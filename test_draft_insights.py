from unittest.mock import Mock
import pytest
from draft_insights import evaluate_pick, slot_suggestions, current_pick, main_champions, save_main_champions
from test_companion import value, slot, gui_app
from test_korean_names import named_app


def analysis_app():
    app = named_app()
    app.my_lane_var = value('top')
    app.recommend_min_games_entry = value('900')
    app.recommend_pick_rate_entry = value('1.5')
    app.is_champion_banned = lambda _: False
    app.is_champion_ignored = lambda _: False
    app.get_lane_weight = lambda target, source, kind: 3 if target == source else 1
    app.banpick_slots = {'allies': [slot('gragas', 'top'), slot('sejuani', 'jungle', synergy_dataset={
        'top': {'Gragas': {'win_rate': 55, 'games': 1500}}})],
        'enemies': [slot('garen', 'top', counter_dataset={
            'top': {'Gragas': {'win_rate': 60, 'games': 2000}}}),
                    slot('ahri', 'middle', counter_dataset={
            'top': {'Gragas': {'win_rate': 40, 'games': 2000}}})]}
    app.champion_data_cache = {'gragas_top.json': {'synergy': {'jungle': {
        'Sejuani': {'win_rate': 57, 'games': 3000}}}, 'counters': {'top': {
        'Garen': {'win_rate': 43, 'games': 3000}}}}}
    return app


def test_current_pick_comparison_uses_both_directions_and_lane_weights():
    app = analysis_app()
    p = evaluate_pick(app, '그라가스')
    assert current_pick(app) == 'gragas'
    assert p['synergy'] == 57
    assert p['counter'] == pytest.approx((43*3+60)/4)
    assert p['total'] == pytest.approx(104.25)
    assert p['lane_matchup'] == {'champion': 'garen', 'win_rate': 43, 'games': 3000}
    assert p['known'] == p['expected'] == 3


def test_low_sample_missing_and_excluded_relations_are_not_invented():
    app = analysis_app()
    app.champion_data_cache['gragas_top.json'] = {'synergy': {}, 'counters': {}}
    app.banpick_slots['allies'][1]['exclude_var'] = value(True)
    app.banpick_slots['enemies'][0]['counter_dataset']['top']['Gragas']['games'] = 2
    p = evaluate_pick(app, 'Gragas')
    assert p['synergy'] is None and p['counter'] == 60
    assert p['lane_matchup'] is None
    assert (p['known'], p['expected']) == (1, 2)
    assert 0 not in p['counter_relations']


@pytest.mark.parametrize('status', ['밴됨', '추천 제외', '다른 슬롯에서 선택됨'])
def test_saved_pick_keeps_score_but_marks_unavailable_status(status):
    app = analysis_app()
    if status == '밴됨':
        app.is_champion_banned = lambda _: True
    elif status == '추천 제외':
        app.is_champion_ignored = lambda _: True
    else:
        app.banpick_slots['enemies'].append(slot('gragas', 'jungle'))
    p = evaluate_pick(app, 'gragas')
    assert p['total'] is not None
    assert p['status'] == status


def test_no_lane_file_or_relations_do_not_show_zero_as_a_real_score():
    app = analysis_app()
    assert evaluate_pick(app, '오른')['total'] is None
    assert evaluate_pick(app, '오른')['status'] == '이 라인 자료 없음'
    app.banpick_slots = {'allies': [slot('gragas', 'top')], 'enemies': []}
    assert evaluate_pick(app, 'gragas')['total'] is None


def test_slot_top_two_are_pair_specific_not_copied_from_overall_ranking():
    rows = [('Gragas', 110), ('Ornn', 108), ('Kennen', 107)]
    components = {'Gragas': {'synergy_relations': {1: {'win_rate': 52, 'games': 1000}}},
                  'Ornn': {'synergy_relations': {1: {'win_rate': 57, 'games': 1000}}},
                  'Kennen': {'synergy_relations': {1: {'win_rate': 58, 'games': 1000}}}}
    assert [r[0] for r in slot_suggestions(rows, components, 'allies', 1)] == ['Kennen', 'Ornn']
    assert slot_suggestions(rows, components, 'enemies', 1) == []


def test_main_champions_persist_per_lane_and_keep_unrelated_settings(tmp_path, monkeypatch):
    import lobby_manager
    app = analysis_app()
    path = tmp_path / 'settings.json'
    monkeypatch.setattr(lobby_manager, 'UI_SETTINGS_FILE', str(path))
    app.ui_settings = {'client_follow': True}
    save_main_champions(app, 'top', ['그라가스', 'Gragas', '오른'])
    save_main_champions(app, 'middle', ['아리'])
    app.ui_settings = app._load_ui_settings()
    assert main_champions(app, 'top') == ['gragas', 'ornn']
    assert main_champions(app, 'middle') == ['ahri']
    assert app.ui_settings['client_follow'] is True
    save_main_champions(app, 'top', ['오른'])
    app.ui_settings = app._load_ui_settings()
    assert main_champions(app, 'top') == ['ornn']


def test_frozen_settings_path_survives_extraction_cleanup(tmp_path, monkeypatch):
    import common
    executable = tmp_path / 'installed' / 'helper.exe'
    monkeypatch.setattr(common.sys, 'frozen', True, raising=False)
    monkeypatch.setattr(common.sys, 'executable', str(executable))
    monkeypatch.setattr(common.sys, '_MEIPASS', str(tmp_path / 'extracted'), raising=False)
    assert common.resolve_writable_path('ui_settings.json') == str(executable.parent / 'ui_settings.json')


def test_failed_settings_save_is_reported_to_the_editor(monkeypatch):
    import lobby_manager
    app = analysis_app()
    app.ui_settings = {}
    def unavailable(*_args):
        raise PermissionError('read-only folder')
    monkeypatch.setattr(lobby_manager.os, 'replace', unavailable)
    # Use a fake file object so the failure check cannot touch real preferences.
    from unittest.mock import mock_open
    monkeypatch.setattr('builtins.open', mock_open())
    assert save_main_champions(app, 'top', ['gragas']) is False


def test_gui_current_pick_and_saved_pick_outside_visible_top_two(gui_app):
    app = gui_app
    app.ui_settings['main_champions'] = {'top': ['gragas', 'ornn']}
    for side, names in (('allies', [('top', '그라가스'), ('jungle', '세주아니'), ('middle', '아칼리'), ('bottom', '진'), ('support', '알리스타')]),
                        ('enemies', [('top', '가렌'), ('jungle', '뽀삐'), ('middle', '아리'), ('bottom', '트위치'), ('support', '레오나')])):
        for lane, name in names:
            target = next(s for s in app.banpick_slots[side] if s['lane'].get() == lane)
            target['entry'].insert(0, name)
            app.perform_banpick_search(target, auto_trigger=True, force_lane=lane)
    app.my_lane_var.set('top')
    ui = app.draft_dashboard
    assert len(ui.cards) == 2
    assert ui.current_profile['champion'] == 'gragas'
    assert ui.favorite_profiles['ornn']['total'] is not None
    assert app.assets.family == 'Pretendard'
    sejuani = next(s for s in app.banpick_slots['allies'] if s['canonical_name'] == 'sejuani')
    assert '현재' in sejuani['comparison_var'].get()
    assert '후보' in sejuani['comparison_var'].get()
    assert '탑 시너지' in sejuani['lane_var'].get()
    assert '1 ' in sejuani['pair_var'].get() and '2 ' in sejuani['pair_var'].get()
    assert '게임' in ui.comparison_note(sejuani)
    assert sejuani['portrait'].cget('image')
    rows = [row for row in ui.recommendations if app.resolve_champion_name(row[0]) != 'ornn'][:2]
    ui.set_recommendations(rows, ui.components)
    ui.favorite_tree.selection_set('ornn')
    ui.select_favorite()
    assert ui.selected_name == 'ornn'
    assert '오른' in ui.detail.get()
    assert '오른' in ui.basis_labels['allies'].cget('text')
    ui.follow.set(False)
    app.root.deiconify()
    app.root.update()
    from companion_layout import Rect, panel_layout
    ui._place_layout(panel_layout(Rect(0, 0, 1920, 1040), Rect(320, 10, 1280, 720)))
    app.root.update()
    for slots in app.banpick_slots.values():
        canvas = slots[0]['frame'].master.master
        assert canvas.yview() == (0.0, 1.0), (canvas.winfo_height(), canvas.bbox('all'),
            slots[0]['frame'].master.winfo_reqheight(), [s['frame'].winfo_reqheight() for s in slots])
        for s in slots:
            row = s['frame']
            assert row.winfo_rooty() + row.winfo_height() <= canvas.winfo_rooty() + canvas.winfo_height()
