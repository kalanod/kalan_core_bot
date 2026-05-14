"""Media inline keyboard helpers tests."""

from app.bot.keyboards.media import build_media_score_text


def test_media_score_text_has_twenty_symbols_for_balanced_score() -> None:
    assert build_media_score_text(approves=1, declines=1) == "🦦" * 10 + "🗿" * 10


def test_media_score_text_handles_empty_counters() -> None:
    assert build_media_score_text(approves=0, declines=0) == "🗿" * 20
