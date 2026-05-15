"""Handlers for Telegram text messages and fan-out broadcasts."""

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.services import TextMessageService, UserStore

REPLY_TARGET_NOT_FOUND_ERRORS = ("replied message", "reply message not found")

router = Router(name="text")


def _is_plain_text(message: Message) -> bool:
    """Return whether a message is regular text and not a bot command."""
    return bool(message.text and not message.text.startswith("/"))


async def resolve_replied_incoming_id(
    *,
    text_service: TextMessageService,
    user_store: UserStore,
    chat_id: int,
    replied_message_id: int,
) -> int | None:
    """Resolve a replied Telegram message to the original incoming text message id.

    The in-memory store is a fast path for the current process, while the database lookup is
    authoritative and keeps reply threading working after deployments or bot restarts.
    """
    cached_id = await user_store.get_replied_incoming_id(
        chat_id=chat_id,
        bot_message_id=replied_message_id,
    )
    if cached_id is not None:
        return cached_id

    return await text_service.find_replied_incoming_id(
        telegram_chat_id=chat_id,
        telegram_message_id=replied_message_id,
    )


async def resolve_recipient_reply_message_id(
    *,
    text_service: TextMessageService,
    user_store: UserStore,
    incoming_message_db_id: int,
    recipient_telegram_id: int,
) -> int | None:
    """Resolve the recipient-local Telegram message id that should be replied to."""
    cached_message_id = await user_store.get_recipient_reply_message_id(
        incoming_message_db_id=incoming_message_db_id,
        recipient_telegram_id=recipient_telegram_id,
    )
    if cached_message_id is not None:
        return cached_message_id

    return await text_service.find_recipient_reply_message_id(
        incoming_message_db_id=incoming_message_db_id,
        recipient_telegram_id=recipient_telegram_id,
    )


@router.message(F.text, _is_plain_text)
async def handle_text(
    message: Message,
    session_factory: async_sessionmaker[AsyncSession],
    user_store: UserStore,
) -> None:
    """Persist incoming text and immediately broadcast it to all known other users."""
    if message.from_user is None or message.text is None:
        return

    sender_telegram_id = message.from_user.id
    if not await user_store.has_user(sender_telegram_id):
        return

    reply_to_text_message_id = None
    if message.reply_to_message is not None:
        async with session_factory() as session:
            reply_to_text_message_id = await resolve_replied_incoming_id(
                text_service=TextMessageService(session),
                user_store=user_store,
                chat_id=message.chat.id,
                replied_message_id=message.reply_to_message.message_id,
            )

    async with session_factory() as session:
        incoming_result = await TextMessageService(session).register_incoming(
            sender_telegram_id=sender_telegram_id,
            telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            text=message.text,
            date=message.date,
            reply_to_text_message_id=reply_to_text_message_id,
        )

    await user_store.add_user(sender_telegram_id)
    recipient_ids = await user_store.other_users(sender_telegram_id)

    for recipient_id in recipient_ids:
        recipient_reply_message_id = None
        if reply_to_text_message_id is not None:
            async with session_factory() as session:
                recipient_reply_message_id = await resolve_recipient_reply_message_id(
                    text_service=TextMessageService(session),
                    user_store=user_store,
                    incoming_message_db_id=reply_to_text_message_id,
                    recipient_telegram_id=recipient_id,
                )

        try:
            sent_message = await message.bot.send_message(
                chat_id=recipient_id,
                text=message.text,
                reply_to_message_id=recipient_reply_message_id,
            )
        except TelegramBadRequest as exc:
            if (
                recipient_reply_message_id is None
                or not any(error_text in exc.message for error_text in REPLY_TARGET_NOT_FOUND_ERRORS)
            ):
                continue

            try:
                sent_message = await message.bot.send_message(
                    chat_id=recipient_id,
                    text=message.text,
                )
            except TelegramAPIError:
                continue
        except TelegramAPIError:
            continue

        async with session_factory() as session:
            await TextMessageService(session).register_outgoing(
                sender_telegram_id=sent_message.from_user.id if sent_message.from_user else 0,
                recipient_telegram_id=recipient_id,
                telegram_chat_id=sent_message.chat.id,
                telegram_message_id=sent_message.message_id,
                text=message.text,
                date=sent_message.date,
                mirrored_from_text_message_id=incoming_result.message.id,
                reply_to_text_message_id=reply_to_text_message_id,
            )

        await user_store.remember_sent_message(
            incoming_message_db_id=incoming_result.message.id,
            recipient_telegram_id=recipient_id,
            chat_id=sent_message.chat.id,
            bot_message_id=sent_message.message_id,
        )
