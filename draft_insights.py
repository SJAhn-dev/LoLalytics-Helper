"""Read-only draft comparisons using the same sample and lane-weight rules."""
from common import LANES


def main_champions(app, lane):
    saved = app.ui_settings.get('main_champions', {})
    names = saved.get(lane, []) if isinstance(saved, dict) else []
    if not isinstance(names, list):
        return []
    resolved = [app.resolve_champion_name(n) for n in names if isinstance(n, str)]
    return list(dict.fromkeys(n for n in resolved if n))[:8]


def save_main_champions(app, lane, names):
    if lane not in LANES:
        raise ValueError('Unknown lane')
    saved = app.ui_settings.get('main_champions')
    if not isinstance(saved, dict):
        saved = {}
    saved[lane] = list(dict.fromkeys(app.resolve_champion_name(n) for n in names))[:8]
    saved[lane] = [n for n in saved[lane] if n]
    app.ui_settings['main_champions'] = saved
    return app._save_ui_settings()


def current_pick(app):
    lane = app.my_lane_var.get()
    return next((s.get('canonical_name') for s in app.banpick_slots['allies']
                 if s['lane'].get() == lane), None)


def evaluate_pick(app, champion):
    """Evaluate a saved/current pick even when it is outside the top 20.

    Missing relations stay missing. A score is a sum of weighted pairwise
    averages, not a predicted probability of winning the whole match.
    """
    lane = app.my_lane_var.get()
    canonical = app.resolve_champion_name(champion)
    result = dict(champion=canonical, total=None, synergy=None, counter=None,
                  synergy_relations={}, counter_relations={}, known=0, expected=0,
                  status='', lane_matchup=None)
    if not canonical or lane not in LANES:
        result['status'] = '라인 선택 필요'
        return result
    raw = app.champion_data_cache.get(f'{canonical}_{lane}.json', {})
    if not raw:
        result['status'] = '이 라인 자료 없음'
    min_games = max(0, app.parse_int(app.recommend_min_games_entry.get()))
    min_pick = max(0, app.parse_float(app.recommend_pick_rate_entry.get()))

    def find(entries, name):
        return next((v for k, v in (entries or {}).items()
                     if app.resolve_champion_name(k) == name), None)

    for side, kind, raw_key in (('allies', 'synergy', 'synergy'),
                                ('enemies', 'counter', 'counters')):
        total, weights = 0.0, 0.0
        for idx, slot in enumerate(app.banpick_slots[side]):
            other = slot.get('canonical_name')
            source_lane = slot.get('selected_lane') or slot['lane'].get()
            if not other or (side == 'allies' and source_lane == lane):
                continue
            if slot.get('exclude_var') and slot['exclude_var'].get():
                continue
            result['expected'] += 1
            a = find((slot.get(kind + '_dataset') or {}).get(lane, {}), canonical)
            payload = raw.get(raw_key, raw if kind == 'counter' else {})
            b = find(payload.get(source_lane, {}), other)
            candidates = []
            for entry, reverse in ((a, side == 'enemies'), (b, False)):
                if not entry:
                    continue
                games = app.parse_int(entry.get('games'))
                popularity = app.parse_float(entry.get('pick_rate') or entry.get('popularity'))
                rate_text = entry.get('win_rate')
                if rate_text is None or not str(rate_text).strip():
                    continue
                rate = app.parse_float(rate_text)
                if not 0 <= rate <= 100 or (games < min_games and popularity < min_pick):
                    continue
                candidates.append((games, 100 - rate if reverse else rate))
            weight = app.get_lane_weight(lane, source_lane, kind)
            if not candidates or weight <= 0:
                continue
            games, rate = max(candidates, key=lambda e: e[0])
            result[kind + '_relations'][idx] = dict(win_rate=rate, games=games)
            result['known'] += 1
            total += rate * weight
            weights += weight
            if side == 'enemies' and source_lane == lane:
                result['lane_matchup'] = dict(champion=other, win_rate=rate, games=games)
        if weights:
            result[kind] = total / weights
    if result['known'] and raw:
        result['total'] = (result['synergy'] or 0) + (result['counter'] or 0)
    elif not result['status']:
        result['status'] = '관계 자료 없음'
    others = [s.get('canonical_name') for side in app.banpick_slots
              for s in app.banpick_slots[side]
              if not (side == 'allies' and s['lane'].get() == lane)]
    if app.is_champion_banned(canonical):
        result['status'] = '밴됨'
    elif canonical in others:
        result['status'] = '다른 슬롯에서 선택됨'
    elif app.is_champion_ignored(canonical):
        result['status'] = '추천 제외'
    return result


def slot_suggestions(recommendations, components, side, index, limit=2):
    """Pair-specific alternatives; overall-draft rankings live in the dock."""
    field = 'synergy_relations' if side == 'allies' else 'counter_relations'
    rows = [(row[0], components.get(row[0], {}).get(field, {}).get(index), row[1])
            for row in recommendations]
    rows = [r for r in rows if r[1] is not None]
    rows.sort(key=lambda r: (r[1]['win_rate'], r[2], r[1].get('games', 0)), reverse=True)
    return rows[:limit]
