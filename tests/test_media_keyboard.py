"""Media inline keyboard helpers tests."""

from app.bot.keyboards.media import build_media_delete_score_keyboard, build_media_score_text


def test_media_score_text_has_twenty_symbols_for_balanced_score() -> None:
    assert build_media_score_text(approves=1, declines=1) == "🦦" * 10 + "🗿" * 10


def test_media_score_text_handles_empty_counters() -> None:
    assert build_media_score_text(approves=0, declines=0) == "🗿" * 10


def test_sender_delete_score_keyboard_uses_progress_bar_and_delete_callback() -> None:
    keyboard = build_media_delete_score_keyboard(
        approves=3,
        declines=1,
        delete_callback_data="mr:1:delete:token",
    )

    button = keyboard.inline_keyboard[0][0]

    assert button.text == "🦦" * 15 + "🗿" * 5
    assert button.callback_data == "mr:1:delete:token"
