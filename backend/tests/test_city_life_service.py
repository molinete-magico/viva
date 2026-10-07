from datetime import datetime, timezone

from app.services.city_life_service import score, normalized


def test_city_life_score_is_deterministic_and_bounded():
    first = score("viva-city-life")
    assert first == score("viva-city-life")
    assert 0 <= first <= 1


def test_city_life_normalizes_sqlite_datetimes():
    value = normalized(datetime(2026, 10, 7, 12, 0))
    assert value.tzinfo == timezone.utc


def test_city_life_keeps_aware_datetimes():
    value = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)
    assert normalized(value) is value


def test_city_life_has_second_order_runner():
    from app.services.city_life_service import _run_city_life_base
    assert callable(_run_city_life_base)
