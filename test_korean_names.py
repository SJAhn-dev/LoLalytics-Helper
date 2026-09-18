"""Official display names must not change search, data keys, or exclusions."""
import json

import pytest

from common import AutocompletePopup
from lobby_manager import ChampionScraperApp, load_alias_tables
import generate_aliases


def named_app():
    app = ChampionScraperApp.__new__(ChampionScraperApp)
    (app.canonical_lookup, app.alias_lookup, app.display_lookup,
     app.autocomplete_candidates) = load_alias_tables()
    return app


@pytest.mark.parametrize("query,canonical,korean", [
    ("Jarvan IV", "jarvaniv", "자르반 4세"),
    ("Nunu & Willump", "nunu", "누누와 윌럼프"),
    ("MonkeyKing", "wukong", "오공"),
    ("K'Sante", "ksante", "크산테"),
    ("Kha'Zix", "khazix", "카직스"),
    ("Rek'Sai", "reksai", "렉사이"),
    ("Vel'Koz", "velkoz", "벨코즈"),
    ("Aurelion Sol", "aurelionsol", "아우렐리온 솔"),
    ("Renata Glasc", "renata", "레나타 글라스크"),
    ("Dr. Mundo", "drmundo", "문도 박사"),
    ("Zaahen", "zaahen", "자헨"),
    ("Locke", "locke", "로크"),
])
def test_official_name_round_trip_preserves_data_identifier(query, canonical, korean):
    app = named_app()
    assert app.resolve_champion_name(query) == canonical
    assert app.resolve_champion_name(korean) == canonical
    assert app.format_display_name(query) == korean
    assert app.format_display_name(canonical) == korean
    assert app.format_display_name(korean) == korean


def test_autocomplete_displays_korean_for_english_queries_and_deduplicates_aliases():
    app = named_app()
    popup = AutocompletePopup.__new__(AutocompletePopup)
    popup.values_provider = app.get_autocomplete_candidates
    popup.display_formatter = app.format_display_name
    popup.max_results = 8
    assert popup._filter_matches("Jarvan") == ["자르반 4세"]
    assert popup._filter_matches("자르반") == ["자르반 4세"]
    assert popup._filter_matches("Nunu") == ["누누와 윌럼프"]


def test_localized_names_resolve_to_the_same_ban_and_ignore_identifiers():
    app = named_app()
    app.ignored_champions = {"nunu"}
    app.banned_champions = {"jarvaniv"}
    assert app.is_champion_ignored("누누와 윌럼프")
    assert app.is_champion_ignored("Nunu & Willump")
    assert app.is_champion_banned("자르반 4세")
    assert app.is_champion_banned("Jarvan IV")


def test_regeneration_keeps_custom_aliases_and_official_spacing(monkeypatch, tmp_path):
    path = tmp_path / "aliases.json"
    path.write_text(json.dumps({"JarvanIV": ["자르반4세", "쟈반"],
                                "jarvaniv": ["자르반"]}), encoding="utf-8")
    monkeypatch.setattr(generate_aliases, "ALIAS_PATH", path)
    monkeypatch.setattr(generate_aliases, "latest_version", lambda: "test")
    monkeypatch.setattr(generate_aliases, "load_locale_data", lambda version, locale: {
        "JarvanIV": {"name": "자르반 4세" if locale == "ko_KR" else "Jarvan IV"}})
    result = generate_aliases.build_aliases()
    assert list(result) == ["jarvaniv"]
    assert result["jarvaniv"][0] == "자르반 4세"
    assert {"자르반4세", "쟈반", "자르반", "Jarvan IV"} <= set(result["jarvaniv"])
