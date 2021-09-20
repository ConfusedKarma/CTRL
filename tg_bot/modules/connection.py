import time
import re

from typing import Optional, List

from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton
from telegram import Message, Chat, Update, Bot, User
from telegram.error import BadRequest, Unauthorized
from telegram.ext import CommandHandler, Filters
from telegram.ext import run_async, CallbackQueryHandler
from telegram.utils.helpers import mention_html

import tg_bot.modules.sql.connection_sql as sql
from tg_bot import dispatcher, LOGGER, SUDO_USERS
from tg_bot.modules.helper_funcs.alternate import send_message
from tg_bot.modules.helper_funcs.chat_status import bot_admin, user_admin, is_user_admin, can_restrict
from tg_bot.modules.helper_funcs.extraction import extract_user, extract_user_and_text
from tg_bot.modules.helper_funcs.string_handling import extract_time

# from tg_bot.modules.translations.strings import tld

from tg_bot.modules.keyboard import keyboard

@user_admin
@run_async
def allow_connections(bot: Bot, update: Update, args: List[str]) -> str:
    chat = update.effective_chat  # type: Optional[Chat]
    if chat.type != chat.PRIVATE and len(args) >= 1:
        var = args[0]
        print(var)
        if (var == "no"):
            sql.set_allow_connect_to_chat(chat.id, False)
            update.effective_message.reply_text("Disabled connections to this chat for users")
        elif(var == "yes"):
            sql.set_allow_connect_to_chat(chat.id, True)
            update.effective_message.reply_text("Enabled connections to this chat for users")
        else:
            update.effective_message.reply_text("Please enter on/yes/off/no in group!")
    else:
        update.effective_message.reply_text("Please enter on/yes/off/no in group!")

@run_async
def connection_chat(bot: Bot, update: Update):

    chat = update.effective_chat
    user = update.effective_user

    conn = connected(bot, update, chat, user.id, need_admin=True)

    if conn:
        chat = dispatcher.bot.getChat(conn)
        chat_name = dispatcher.bot.getChat(conn).title
    else:
        if update.effective_message.chat.type != "private":
            return
        chat = update.effective_chat
        chat_name = update.effective_message.chat.title

    if conn:
        message = "You are currently connected to {}.\n".format(chat_name)
    else:
        message = "You are currently not connected to any group.\n"
    send_message(update.effective_message, message, parse_mode=ParseMode.MARKDOWN)

@run_async
def connect_chat(bot, update, args):

    chat = update.effective_chat
    user = update.effective_user

    if update.effective_chat.type == "private":
        if len(args) >= 1:
            try:
                connect_chat = int(args[0])
                getstatusadmin = context.bot.get_chat_member(
                    connect_chat, update.effective_message.from_user.id
                )
            except ValueError:
                try:
                    connect_chat = str(args[0])
                    get_chat = bot.getChat(connect_chat)
                    connect_chat = get_chat.id
                    getstatusadmin = bot.get_chat_member(
                        connect_chat, update.effective_message.from_user.id
                    )
                except BadRequest:
                    send_message(update.effective_message, "Invalid Chat ID!")
                    return
            except BadRequest:
                send_message(update.effective_message, "Invalid Chat ID!")
                return

            isadmin = getstatusadmin.status in ("administrator", "creator")
            ismember = getstatusadmin.status in ("member")
            isallow = sql.allow_connect_to_chat(connect_chat)

            if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
                connection_status = sql.connect(
                    update.effective_message.from_user.id, connect_chat
                )
                if connection_status:
                    conn_chat = dispatcher.bot.getChat(
                        connected(bot, update, chat, user.id, need_admin=False)
                    )
                    chat_name = conn_chat.title
                    send_message(
                        update.effective_message,
                        "Successfully connected to *{}*. \nUse /helpconnect to check available commands.".format(
                            chat_name
                        ),
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
                else:
                    send_message(update.effective_message, "Connection failed!")
            else:
                send_message(
                    update.effective_message, "Connection to this chat is not allowed!"
                )
        else:
            gethistory = sql.get_history_conn(user.id)
            if gethistory:
                buttons = [
                    InlineKeyboardButton(
                        text="❎ Close button", callback_data="connect_close"
                    ),
                    InlineKeyboardButton(
                        text="🧹 Clear history", callback_data="connect_clear"
                    ),
                ]
            else:
                buttons = []
            conn = connected(bot, update, chat, user.id, need_admin=False)
            if conn:
                connectedchat = dispatcher.bot.getChat(conn)
                text = "You are currently connected to *{}* (`{}`)".format(
                    connectedchat.title, conn
                )
                buttons.append(
                    InlineKeyboardButton(
                        text="🔌 Disconnect", callback_data="connect_disconnect"
                    )
                )
            else:
                text = "Write the chat ID or tag to connect!"
            if gethistory:
                text += "\n\n*Connection history:*\n"
                text += "╒═══「 *Info* 」\n"
                text += "│  Sorted: `Newest`\n"
                text += "│\n"
                buttons = [buttons]
                for x in sorted(gethistory.keys(), reverse=True):
                    htime = time.strftime("%d/%m/%Y", time.localtime(x))
                    text += "╞═「 *{}* 」\n│   `{}`\n│   `{}`\n".format(
                        gethistory[x]["chat_name"], gethistory[x]["chat_id"], htime
                    )
                    text += "│\n"
                    buttons.append(
                        [
                            InlineKeyboardButton(
                                text=gethistory[x]["chat_name"],
                                callback_data="connect({})".format(
                                    gethistory[x]["chat_id"]
                                ),
                            )
                        ]
                    )
                text += "╘══「 Total {} Chats 」".format(
                    str(len(gethistory)) + " (max)"
                    if len(gethistory) == 5
                    else str(len(gethistory))
                )
                conn_hist = InlineKeyboardMarkup(buttons)
            elif buttons:
                conn_hist = InlineKeyboardMarkup([buttons])
            else:
                conn_hist = None
            send_message(
                update.effective_message,
                text,
                parse_mode="markdown",
                reply_markup=conn_hist,
            )

    else:
        getstatusadmin = bot.get_chat_member(
            chat.id, update.effective_message.from_user.id
        )
        isadmin = getstatusadmin.status in ("administrator", "creator")
        ismember = getstatusadmin.status in ("member")
        isallow = sql.allow_connect_to_chat(chat.id)
        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            connection_status = sql.connect(
                update.effective_message.from_user.id, chat.id
            )
            if connection_status:
                chat_name = dispatcher.bot.getChat(chat.id).title
                send_message(
                    update.effective_message,
                    "Successfully connected to *{}*.".format(chat_name),
                    parse_mode=ParseMode.MARKDOWN,
                )
                try:
                    sql.add_history_conn(user.id, str(chat.id), chat_name)
                    bot.send_message(
                        update.effective_message.from_user.id,
                        "You are connected to *{}*.".format(
                            chat_name
                        ),
                        parse_mode="markdown",
                    )
                except BadRequest:
                    pass
                except Unauthorized:
                    pass
            else:
                send_message(update.effective_message, "Connection failed!")
        else:
            send_message(
                update.effective_message, "Connection to this chat is not allowed!"
            )


def disconnect_chat(bot, update):
    if update.effective_chat.type == 'private':
        disconnection_status = sql.disconnect(update.effective_message.from_user.id)
        if disconnection_status:
            sql.disconnected_chat = update.effective_message.reply_text("Disconnected from chat!")
            #Rebuild user's keyboard
            keyboard(bot, update)
        else:
           update.effective_message.reply_text("Disconnection unsuccessfull!")
    else:
        update.effective_message.reply_text("Usage limited to PMs only")


def connected(bot, update, chat, user_id, need_admin=True):
    if chat.type != chat.PRIVATE or not sql.get_connected_chat(user_id):
        return False
    conn_id = sql.get_connected_chat(user_id).chat_id
    if (bot.get_chat_member(conn_id, user_id).status in ('administrator', 'creator') or 
                                     (sql.allow_connect_to_chat(connect_chat) == True) and 
                                     bot.get_chat_member(user_id, update.effective_message.from_user.id).status in ('member')) or (
                                     user_id in SUDO_USERS):
        if need_admin != True:
            return conn_id
        if bot.get_chat_member(conn_id, update.effective_message.from_user.id).status in ('administrator', 'creator') or user_id in SUDO_USERS:
            return conn_id
        update.effective_message.reply_text("You need to be a admin in a connected group!")
    else:
        update.effective_message.reply_text("Group changed rights connection or you are not admin anymore.\nI'll disconnect you.")
        disconnect_chat(bot, update)
    exit(1)

run_async
def connect_button(bot, update):

    query = update.callback_query
    chat = update.effective_chat
    user = update.effective_user

    connect_match = re.match(r"connect\((.+?)\)", query.data)
    disconnect_match = query.data == "connect_disconnect"
    clear_match = query.data == "connect_clear"
    connect_close = query.data == "connect_close"

    if connect_match:
        target_chat = connect_match.group(1)
        getstatusadmin = bot.get_chat_member(target_chat, query.from_user.id)
        isadmin = getstatusadmin.status in ("administrator", "creator")
        ismember = getstatusadmin.status in ("member")
        isallow = sql.allow_connect_to_chat(target_chat)

        if (isadmin) or (isallow and ismember) or (user.id in SUDO_USERS):
            connection_status = sql.connect(query.from_user.id, target_chat)

            if connection_status:
                conn_chat = dispatcher.bot.getChat(
                    connected(bot, update, chat, user.id, need_admin=False)
                )
                chat_name = conn_chat.title
                query.message.edit_text(
                    "Successfully connected to *{}*.".format(
                        chat_name
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
                sql.add_history_conn(user.id, str(conn_chat.id), chat_name)
            else:
                query.message.edit_text("Connection failed!")
        else:
            bot.answer_callback_query(
                query.id, "Connection to this chat is not allowed!", show_alert=True
            )
    elif disconnect_match:
        disconnection_status = sql.disconnect(query.from_user.id)
        if disconnection_status:
            sql.disconnected_chat = query.message.edit_text("Disconnected from chat!")
        else:
            bot.answer_callback_query(
                query.id, "You're not connected!", show_alert=True
            )
    elif clear_match:
        sql.clear_history_conn(query.from_user.id)
        query.message.edit_text("History connected has been cleared!")
    elif connect_close:
        query.message.edit_text("Closed.\nTo open again, type /connect")
    else:
        connect_chat(bot, update)

__help__ = """
Actions are available with connected groups:
 • View and edit notes
 • View and edit filters
 • Get invite link of chat.
 • Enable and Disable commands in chat.
 • Set and control AntiFlood settings.
 • Set and control Blacklist settings.
 • Export and Imports of chat backup.
 • More in future!


 • /connect: Connects to chat (Can be done in a group by /connect or /connect <chat id> in PM)
 • /connection: List connected chats
 • /disconnect: Disconnect from a chat

*Admin only:*
 • /allowconnect <yes/no>: allow a user to connect to a chat
"""



__mod_name__ = "Connections"

CONNECT_CHAT_HANDLER = CommandHandler("connect", connect_chat, allow_edited=True, pass_args=True)
DISCONNECT_CHAT_HANDLER = CommandHandler("disconnect", disconnect_chat, allow_edited=True)
CONNECTION_CHAT_HANDLER = CommandHandler("connection", connection_chat, allow_edited=True)
ALLOW_CONNECTIONS_HANDLER = CommandHandler("allowconnect", allow_connections, allow_edited=True, pass_args=True)
CONNECT_BTN_HANDLER = CallbackQueryHandler(connect_button, pattern=r"connect")

dispatcher.add_handler(CONNECT_CHAT_HANDLER)
dispatcher.add_handler(CONNECTION_CHAT_HANDLER)
dispatcher.add_handler(DISCONNECT_CHAT_HANDLER)
dispatcher.add_handler(ALLOW_CONNECTIONS_HANDLER)
dispatcher.add_handler(CONNECT_BTN_HANDLER)
