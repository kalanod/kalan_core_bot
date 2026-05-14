"""Handlers for supported Telegram media messages."""

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.keyboards.media import build_media_reaction_keyboard, build_media_score_keyboard
from app.bot.services import MediaMessageService, UserStore
from app.bot.utils.media import extract_media

router = Router(name="media")


@router.message(F.photo | F.video)
async def handle_media(
    message: Message,
    session_factory: async_sessionmaker[AsyncSession],
    user_store: UserStore,
) -> None:
    """Persist incoming media and immediately broadcast it with per-user buttons."""
    if message.from_user is None:
        return

    media = extract_media(message)
    if media is None:
        await message.answer("Пока я умею сохранять только фото и видео.")
        return

    sender_telegram_id = message.from_user.id
    async with session_factory() as session:
        incoming_result = await MediaMessageService(session).register_incoming(
            sender_telegram_id=sender_telegram_id,
            telegram_chat_id=message.chat.id,
            telegram_message_id=message.message_id,
            telegram_file_id=media.file_id,
            media_type=media.media_type,
            caption=message.caption,
            date=message.date,
        )

    await user_store.add_user(sender_telegram_id)
    recipient_ids = await user_store.other_users(sender_telegram_id)

    for recipient_id in recipient_ids:
        async with session_factory() as session:
            prepared_delivery = await MediaMessageService(session).prepare_delivery(
                incoming_media_message_id=incoming_result.message.id,
                recipient_telegram_id=recipient_id,
            )

        reply_markup = build_media_reaction_keyboard(
            otter_callback_data=prepared_delivery.otter_callback_data,
            stone_face_callback_data=prepared_delivery.stone_face_callback_data,
        )
        try:
            if media.media_type == "photo":
                sent_message = await message.bot.send_photo(
                    chat_id=recipient_id,
                    photo=media.file_id,
                    caption=message.caption,
                    reply_markup=reply_markup,
                )
            else:
                sent_message = await message.bot.send_video(
                    chat_id=recipient_id,
                    video=media.file_id,
                    caption=message.caption,
                    reply_markup=reply_markup,
                )
        except TelegramAPIError as error:
            async with session_factory() as session:
                await MediaMessageService(session).register_delivery_failure(
                    delivery_id=prepared_delivery.delivery.id,
                    error=str(error),
                )
            continue

        async with session_factory() as session:
            await MediaMessageService(session).register_outgoing(
                sender_telegram_id=sent_message.from_user.id if sent_message.from_user else 0,
                recipient_telegram_id=recipient_id,
                telegram_chat_id=sent_message.chat.id,
                telegram_message_id=sent_message.message_id,
                media_type=media.media_type,
                caption=message.caption,
                date=sent_message.date,
                kalan_id=incoming_result.message.kalan_id,
                mirrored_from_media_message_id=incoming_result.message.id,
                delivery_id=prepared_delivery.delivery.id,
            )

    if incoming_result.kalan_created:
        await message.answer("Калан сохранён и разослан ✅")
        return

    await message.answer("Этот калан уже был сохранён ранее, новая отправка разослана.")


@router.callback_query(F.data.startswith("mr:"))
async def handle_media_reaction_callback(
    callback: CallbackQuery,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Apply or undo media reactions and update the inline keyboard."""
    if callback.data is None:
        await callback.answer("Неизвестная кнопка", show_alert=True)
        return

    async with session_factory() as session:
        result = await MediaMessageService(session).register_reaction_click(
            callback_data=callback.data,
            user_telegram_id=callback.from_user.id,
        )

    if result.status == "not_found":
        await callback.answer("Кнопка не найдена или не для вас", show_alert=True)
        return

    if result.status == "applied":
        if result.undo_callback_data is not None and callback.message is not None:
            await callback.message.edit_reply_markup(
                reply_markup=build_media_score_keyboard(
                    approves=result.approves,
                    declines=result.declines,
                    undo_callback_data=result.undo_callback_data,
                )
            )
        await callback.answer("Голос учтён")
        return

    if result.status == "cancelled":
        if (
            result.otter_callback_data is not None
            and result.stone_face_callback_data is not None
            and callback.message is not None
        ):
            await callback.message.edit_reply_markup(
                reply_markup=build_media_reaction_keyboard(
                    otter_callback_data=result.otter_callback_data,
                    stone_face_callback_data=result.stone_face_callback_data,
                )
            )
        await callback.answer("Голос отменён")
        return

    await callback.answer("Голос уже отменён")
