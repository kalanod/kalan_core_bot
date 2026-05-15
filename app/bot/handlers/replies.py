"""Shared Telegram reply resolution helpers for broadcast handlers."""

from app.bot.services import MessageReference, MessageReplyService, UserStore

REPLY_TARGET_NOT_FOUND_ERRORS = ("replied message", "reply message not found")


async def resolve_replied_incoming_ref(
    *,
    reply_service: MessageReplyService,
    user_store: UserStore,
    chat_id: int,
    replied_message_id: int,
) -> MessageReference | None:
    """Resolve a replied Telegram message to the original incoming broadcast reference."""
    cached_ref = await user_store.get_replied_incoming_ref(
        chat_id=chat_id,
        bot_message_id=replied_message_id,
    )
    if cached_ref is not None:
        return cached_ref

    return await reply_service.find_replied_incoming_ref(
        telegram_chat_id=chat_id,
        telegram_message_id=replied_message_id,
    )


async def resolve_recipient_broadcast_reply_message_id(
    *,
    reply_service: MessageReplyService,
    user_store: UserStore,
    incoming_message: MessageReference,
    recipient_telegram_id: int,
) -> int | None:
    """Resolve the recipient-local Telegram message id that should be replied to."""
    cached_message_id = await user_store.get_recipient_broadcast_reply_message_id(
        incoming_message=incoming_message,
        recipient_telegram_id=recipient_telegram_id,
    )
    if cached_message_id is not None:
        return cached_message_id

    return await reply_service.find_recipient_reply_message_id(
        incoming_message=incoming_message,
        recipient_telegram_id=recipient_telegram_id,
    )
