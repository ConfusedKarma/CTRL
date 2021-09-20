import re
from typing import Optional
import html
import telegram
from telegram import ParseMode, InlineKeyboardMarkup, Message, Chat, InlineKeyboardButton
from telegram import Update, Bot
from telegram.error import BadRequest
from telegram.ext import CommandHandler, MessageHandler, DispatcherHandlerStop, run_async, Filters, CallbackQueryHandler
from telegram.utils.helpers import escape_markdown, mention_html
from html import escape

from tg_bot import dispatcher, LOGGER, SUDO_USERS
from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot.modules.helper_funcs.chat_status import user_admin
from tg_bot.modules.helper_funcs.extraction import extract_text
from tg_bot.modules.helper_funcs.filters import CustomFilters
from tg_bot.modules.helper_funcs.msg_types import get_filter_type
from tg_bot.modules.helper_funcs.misc import build_keyboard_parser
from tg_bot.modules.helper_funcs.string_handling import (
    split_quotes,
    button_markdown_parser,
    escape_invalid_curly_brackets,
    markdown_to_html,
)
from tg_bot.modules.sql import cust_filters_sql as sql

from tg_bot.modules.helper_funcs.alternate import send_message

from tg_bot.modules.connection import connected

HANDLER_GROUP = 15

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video,
    sql.Types.VIDEO_NOTE.value: dispatcher.bot.send_video_note
}

def escape_html(word):
    return escape(word)


@run_async
def list_handlers(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user

    conn = connected(bot, update, chat, user.id, need_admin=False)
    if conn != False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
        filter_list = "*List of filters in {}:*\n"
    else:
        chat_id = update.effective_chat.id
        if chat.type == "private":
            chat_name = "Local filters"
            filter_list = "*local filters:*\n"
        else:
            chat_name = chat.title
            filter_list = "*Filters in {}*:\n"

    all_handlers = sql.get_chat_triggers(chat_id)

    if not all_handlers:
        send_message(
            update.effective_message, "No filters in {}!".format(chat_name)
        )
        return

    for keyword in all_handlers:
        entry = " • `{}`\n".format(escape_markdown(keyword))
        if len(entry) + len(filter_list) > telegram.MAX_MESSAGE_LENGTH:
            send_message(
                update.effective_message,
                filter_list.format(chat_name),
                parse_mode=telegram.ParseMode.MARKDOWN,
            )
            filter_list = entry
        else:
            filter_list += entry

    send_message(
        update.effective_message,
        filter_list.format(chat_name),
        parse_mode=telegram.ParseMode.MARKDOWN,
    )

# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def filters(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    msg = update.effective_message
    args = msg.text.split(
        None, 1
    )  # use python's maxsplit to separate Cmd, keyword, and reply_text

    conn = connected(bot, update, chat, user.id)
    if conn != False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        chat_name = "local filters" if chat.type == "private" else chat.title
    if not msg.reply_to_message and len(args) < 2:
        send_message(
            update.effective_message,
            "Please provide keyboard keyword for this filter to reply with!",
        )
        return

    if msg.reply_to_message:
        if len(args) < 2:
            send_message(
                update.effective_message,
                "Please provide keyword for this filter to reply with!",
            )
            return
        else:
            keyword = args[1]
    else:
        extracted = split_quotes(args[1])
        if len(extracted) < 1:
            return
        # set trigger -> lower, so as to avoid adding duplicate filters with different cases
        keyword = extracted[0].lower()

    # Add the filter
    # Note: perhaps handlers can be removed somehow using sql.get_chat_filters
    for handler in dispatcher.handlers.get(HANDLER_GROUP, []):
        if handler.filters == (keyword, chat_id):
            dispatcher.remove_handler(handler, HANDLER_GROUP)

    text, file_type, file_id = get_filter_type(msg)
    if not msg.reply_to_message and len(extracted) >= 2:
        offset = len(extracted[1]) - len(
            msg.text
        )  # set correct offset relative to command + notename
        text, buttons = button_markdown_parser(
            extracted[1], entities=msg.parse_entities(), offset=offset
        )
        text = text.strip()
        if not text:
            send_message(
                update.effective_message,
                "There is no note message - You can't JUST have buttons, you need a message to go with it!",
            )
            return

    elif msg.reply_to_message and len(args) >= 2:
        if msg.reply_to_message.text:
            text_to_parsing = msg.reply_to_message.text
        elif msg.reply_to_message.caption:
            text_to_parsing = msg.reply_to_message.caption
        else:
            text_to_parsing = ""
        offset = len(
            text_to_parsing
        )  # set correct offset relative to command + notename
        text, buttons = button_markdown_parser(
            text_to_parsing, entities=msg.parse_entities(), offset=offset
        )
        text = text.strip()

    elif not text and not file_type:
        send_message(
            update.effective_message,
            "Please provide keyword for this filter reply with!",
        )
        return

    elif msg.reply_to_message:
        if msg.reply_to_message.text:
            text_to_parsing = msg.reply_to_message.text
        elif msg.reply_to_message.caption:
            text_to_parsing = msg.reply_to_message.caption
        else:
            text_to_parsing = ""
        offset = len(
            text_to_parsing
        )  # set correct offset relative to command + notename
        text, buttons = button_markdown_parser(
            text_to_parsing, entities=msg.parse_entities(), offset=offset
        )
        text = text.strip()
        if (msg.reply_to_message.text or msg.reply_to_message.caption) and not text:
            send_message(
                update.effective_message,
                "There is no note message - You can't JUST have buttons, you need a message to go with it!",
            )
            return

    else:
        send_message(update.effective_message, "Invalid filter!")
        return

    add = addnew_filter(update, chat_id, keyword, text, file_type, file_id, buttons)
    # This is an old method
    # sql.add_filter(chat_id, keyword, content, is_sticker, is_document, is_image, is_audio, is_voice, is_video, buttons)

    if add == True:
        send_message(
            update.effective_message,
            "Saved filter '{}' in *{}*!".format(keyword, chat_name),
            parse_mode=telegram.ParseMode.MARKDOWN,
        )
    raise DispatcherHandlerStop


# NOT ASYNC BECAUSE DISPATCHER HANDLER RAISED
@user_admin
def stop_filter(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    args = update.effective_message.text.split(None, 1)

    conn = connected(bot, update, chat, user.id)
    if conn != False:
        chat_id = conn
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        chat_id = update.effective_chat.id
        chat_name = "Local filters" if chat.type == "private" else chat.title
    if len(args) < 2:
        send_message(update.effective_message, "What should i stop?")
        return

    chat_filters = sql.get_chat_triggers(chat_id)

    if not chat_filters:
        send_message(update.effective_message, "No filters are active in {}!").format(chat_name)
        return

    for keyword in chat_filters:
        if keyword == args[1]:
            sql.remove_filter(chat_id, args[1])
            send_message(
                update.effective_message,
                "Yep, I'll stop replying to that filter in *{}*.".format(chat_name),
                parse_mode=telegram.ParseMode.MARKDOWN,
            )
            raise DispatcherHandlerStop

    send_message(
        update.effective_message,
        "That's not a current filter - run: /filters to get currently active filters.",
    )


@run_async
def reply_filter(bot: Bot, update: Update):
    chat = update.effective_chat  # type: Optional[Chat]
    message = update.effective_message  # type: Optional[Message]

    to_match = extract_text(message)
    if not to_match:
        return

    chat_filters = sql.get_chat_triggers(chat.id)
    for keyword in chat_filters:
        pattern = r"( |^|[^\w])" + re.escape(keyword) + r"( |$|[^\w])"
        if re.search(pattern, to_match, flags=re.IGNORECASE):
            filt = sql.get_filter(chat.id, keyword)
            if filt.reply == "there is should be a new reply":
                buttons = sql.get_buttons(chat.id, filt.keyword)
                keyb = build_keyboard_parser(bot, chat.id, buttons)
                keyboard = InlineKeyboardMarkup(keyb)

                VALID_WELCOME_FORMATTERS = [
                    "first",
                    "last",
                    "fullname",
                    "username",
                    "id",
                    "chatname",
                    "mention",
                ]
                if filt.reply_text:
                    valid_format = escape_invalid_curly_brackets(
                        filt.reply_text, VALID_WELCOME_FORMATTERS
                    )
                    if valid_format:
                        filtext = valid_format.format(
                            first=escape(message.from_user.first_name),
                            last=escape(
                                message.from_user.last_name
                                or message.from_user.first_name
                            ),
                            fullname=" ".join(
                                [
                                    escape(message.from_user.first_name),
                                    escape(message.from_user.last_name),
                                ]
                                if message.from_user.last_name
                                else [escape(message.from_user.first_name)]
                            ),
                            username="@" + escape(message.from_user.username)
                            if message.from_user.username
                            else mention_html(
                                message.from_user.id, message.from_user.first_name
                            ),
                            mention=mention_html(
                                message.from_user.id, message.from_user.first_name
                            ),
                            chatname=escape(message.chat.title)
                            if message.chat.type != "private"
                            else escape(message.from_user.first_name),
                            id=message.from_user.id,
                        )
                    else:
                        filtext = ""
                else:
                    filtext = ""

                if filt.file_type in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    try:
                        bot.send_message(
                            chat.id,
                            markdown_to_html(filtext),
                            reply_to_message_id=message.message_id,
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True,
                            reply_markup=keyboard,
                        )
                    except BadRequest as excp:
                        error_catch = get_exception(excp, filt, chat)
                        if error_catch == "noreply":
                            try:
                                bot.send_message(
                                    chat.id,
                                    markdown_to_html(filtext),
                                    parse_mode=ParseMode.HTML,
                                    disable_web_page_preview=True,
                                    reply_markup=keyboard,
                                )
                            except BadRequest as excp:
                                LOGGER.exception("Error in filters: " + excp.message)
                                send_message(
                                    update.effective_message,
                                    get_exception(excp, filt, chat),
                                )
                        else:
                            try:
                                send_message(
                                    update.effective_message,
                                    get_exception(excp, filt, chat),
                                )
                            except BadRequest as excp:
                                LOGGER.exception(
                                    "Failed to send message: " + excp.message
                                )
                else:
                    ENUM_FUNC_MAP[filt.file_type](
                        chat.id,
                        filt.file_id,
                        caption=markdown_to_html(filtext),
                        reply_to_message_id=message.message_id,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                        reply_markup=keyboard,
                    )
            else:
                if filt.is_sticker:
                    message.reply_sticker(filt.reply)
                elif filt.is_document:
                    message.reply_document(filt.reply)
                elif filt.is_image:
                    message.reply_photo(filt.reply)
                elif filt.is_audio:
                    message.reply_audio(filt.reply)
                elif filt.is_voice:
                    message.reply_voice(filt.reply)
                elif filt.is_video:
                    message.reply_video(filt.reply)
                elif filt.has_markdown:
                    buttons = sql.get_buttons(chat.id, filt.keyword)
                    keyb = build_keyboard_parser(bot, chat.id, buttons)
                    keyboard = InlineKeyboardMarkup(keyb)

                    try:
                        send_message(
                            update.effective_message,
                            filt.reply,
                            parse_mode=ParseMode.MARKDOWN,
                            disable_web_page_preview=True,
                            reply_markup=keyboard,
                        )
                    except BadRequest as excp:
                        if excp.message == "Unsupported url protocol":
                            try:
                                send_message(
                                    update.effective_message,
                                    "You seem to be trying to use an unsupported url protocol. "
                                    "Telegram doesn't support buttons for some protocols, such as tg://. Please try "
                                    "again...",
                                )
                            except BadRequest as excp:
                                LOGGER.exception("Error in filters: " + excp.message)
                        elif excp.message == "Reply message not found":
                            try:
                                bot.send_message(
                                    chat.id,
                                    filt.reply,
                                    parse_mode=ParseMode.MARKDOWN,
                                    disable_web_page_preview=True,
                                    reply_markup=keyboard,
                                )
                            except BadRequest as excp:
                                LOGGER.exception("Error in filters: " + excp.message)
                        else:
                            try:
                                send_message(
                                    update.effective_message,
                                    "This message couldn't be sent as it's incorrectly formatted.",
                                )
                            except BadRequest as excp:
                                LOGGER.exception("Error in filters: " + excp.message)
                            LOGGER.warning(
                                "Message %s could not be parsed", str(filt.reply)
                            )
                            LOGGER.exception(
                                "Could not parse filter %s in chat %s",
                                str(filt.keyword),
                                str(chat.id),
                            )

                else:
                    # LEGACY - all new filters will have has_markdown set to True.
                    try:
                        send_message(update.effective_message, filt.reply)
                    except BadRequest as excp:
                        LOGGER.exception("Error in filters: " + excp.message)

            break


@user_admin
def rmall_filters(bot: Bot, update: Update):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in SUDO_USERS:
        update.effective_message.reply_text(
            "Only the chat owner can clear all notes at once.")
    else:
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text="Stop all filters", callback_data="filters_rmall")
        ], [
            InlineKeyboardButton(text="Cancel", callback_data="filters_cancel")
        ]])
        update.effective_message.reply_text(
            f"⚠️ Are you sure ,you want to remove all filters in {chat.title}? This action cannot be undone.",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN)


@run_async
def rmall_callback(bot: Bot, update: Update):
    query = update.callback_query
    chat = update.effective_chat
    msg = update.effective_message
    member = chat.get_member(query.from_user.id)
    if query.data == 'filters_rmall':
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            allfilters = sql.get_chat_triggers(chat.id)
            if not allfilters:
                msg.edit_text("No filters in this chat, nothing to stop!")
                return

            count = 0
            filterlist = []
            for x in allfilters:
                count += 1
                filterlist.append(x)

            for i in filterlist:
                sql.remove_filter(chat.id, i)

            msg.edit_text(f"Cleaned {count} filters in {chat.title}")

        if member.status == "administrator":
            query.answer("Only owner of the chat can do this.")

        if member.status == "member":
            query.answer("You need to be admin to do this.")
    elif query.data == 'filters_cancel':
        if member.status == "creator" or query.from_user.id in SUDO_USERS:
            msg.edit_text("Clearing of all filters has been cancelled.")
            return
        if member.status == "administrator":
            query.answer("Only owner of the chat can do this.")
        if member.status == "member":
            query.answer("You need to be admin to do this.")


# NOT ASYNC NOT A HANDLER
def get_exception(excp, filt, chat):
    if excp.message == "Unsupported url protocol":
        return "You seem to be trying to use the URL protocol which is not supported. Telegram does not support key for multiple protocols, such as tg: //. Please try again!"
    elif excp.message == "Reply message not found":
        return "noreply"
    else:
        LOGGER.warning("Message %s could not be parsed", str(filt.reply))
        LOGGER.exception("Could not parse filter %s in chat %s",
                         str(filt.keyword), str(chat.id))
        return "This data could not be sent because it is incorrectly formatted."

# NOT ASYNC NOT A HANDLER
def addnew_filter(update, chat_id, keyword, text, file_type, file_id, buttons):
    msg = update.effective_message
    totalfilt = sql.get_chat_triggers(chat_id)
    if len(totalfilt) >= 50:  # Idk why i made this like function....
        msg.reply_text(
            "You can't have more that fifty filters at once! try removing some before adding new filters."
        )
        return False
    else:
        sql.new_add_filter(chat_id, keyword, text, file_type, file_id, buttons)
        return True


def __stats__():
    return "{} filters, across {} chats.".format(sql.num_filters(), sql.num_chats())


def __import_data__(chat_id, data):
    # set chat filters
    filters = data.get("filters", {})
    for trigger in filters:
        sql.add_to_blacklist(chat_id, trigger)

def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(bot, update, chat, chatP, user):
    cust_filters = sql.get_chat_triggers(chat.id)
    return "There are `{}` custom filters here.".format(len(cust_filters))


__help__ = """
Make your chat more lively with filters; The bot will reply to certain words!
Filters are case insensitive; every time someone says your trigger words, {} will reply something else! can be used to create your own commands, if desired.
 - /filters: list all active filters in this chat.
*Admin only:*
 - /filter <keyword> <reply message>: Every time someone says "word", the bot will reply with "sentence". For multiple word filters, quote the first word.
 - /stop <filter keyword>: stop that filter.
 
 An example of how to set a filter would be via:
`/filter hello Hello there! How are you?`
A multiword filter could be set via:
`/filter "hello friend" Hello back! Long time no see!`
If you want to save an image, gif, or sticker, or any other data, do the following:
`/filter word while replying to a sticker or whatever data you'd like. Now, every time someone mentions "word", that sticker will be sent as a reply.`
Now, anyone saying "hello" will be replied to with "Hello there! How are you?".


*Chat creator only:*
 × /rmallfilter: Stop all chat filters at once.
"""

__mod_name__ = "Filters"

FILTER_HANDLER = DisableAbleCommandHandler("filter", filters)
STOP_HANDLER = DisableAbleCommandHandler("stop", stop_filter)
RMALLFILTER_HANDLER = CommandHandler(
    "rmallfilter", rmall_filters, filters=Filters.group
)
RMALLFILTER_CALLBACK = CallbackQueryHandler(
    rmall_callback, pattern=r"filters_.*")
LIST_HANDLER = DisableAbleCommandHandler("filters", list_handlers, admin_ok=True)
CUST_FILTER_HANDLER = MessageHandler(CustomFilters.has_text, reply_filter)

dispatcher.add_handler(FILTER_HANDLER)
dispatcher.add_handler(STOP_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(CUST_FILTER_HANDLER, HANDLER_GROUP)
dispatcher.add_handler(RMALLFILTER_HANDLER)
dispatcher.add_handler(RMALLFILTER_CALLBACK)
