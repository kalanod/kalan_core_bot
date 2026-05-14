"""Handlers for Telegram text messages and fan-out broadcasts."""

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.services import TextMessageService, UserStore

router = Router(name="text")


def _is_plain_text(message: Message) -> bool:
    """Return whether a message is regular text and not a bot command."""
    return bool(message.text and not message.text.startswith("/"))


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
    reply_to_text_message_id = None
    if message.reply_to_message is not None:
        reply_to_text_message_id = await user_store.get_replied_incoming_id(
            chat_id=message.chat.id,
            bot_message_id=message.reply_to_message.message_id,
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
            recipient_reply_message_id = await user_store.get_recipient_reply_message_id(
                incoming_message_db_id=reply_to_text_message_id,
                recipient_telegram_id=recipient_id,
            )

        try:
            sent_message = await message.bot.send_message(
                chat_id=recipient_id,
                text=message.text,
                reply_to_message_id=recipient_reply_message_id,
            )
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
