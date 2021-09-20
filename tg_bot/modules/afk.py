from typing import Optional
import html

from telegram import Message, Update, Bot, User
from telegram import MessageEntity, ParseMode
from telegram.error import BadRequest
from telegram.ext import Filters, MessageHandler, run_async

from tg_bot import dispatcher
from tg_bot.modules.disable import DisableAbleCommandHandler, DisableAbleRegexHandler
from tg_bot.modules.sql import afk_sql as sql
from tg_bot.modules.users import get_user_id


AFK_GROUP = 7
AFK_REPLY_GROUP = 8


@run_async
def afk(bot: Bot, update: Update):
    user = update.effective_user
    args = update.effective_message.text.split(None, 1)

    if not user:
        return

    if user.id in (777000, 1087968824):
        return

    reason = args[1] if len(args) >= 2 else ""
    sql.set_afk(update.effective_user.id, reason)
    fname = update.effective_user.first_name
    update.effective_message.reply_text(f"{fname} is now AFK!")


@run_async
def no_longer_afk(bot: Bot, update: Update):
    user = update.effective_user  # type: Optional[User]

    if not user:  # ignore channels
        return

    res = sql.rm_afk(user.id)
    if res:
        firstname = update.effective_user.first_name
        try:
            update.effective_message.reply_text(f"{firstname} is no longer AFK!")
        except:
            return


@run_async
def reply_afk(bot: Bot, update: Update):
    message = update.effective_message  # type: Optional[Message]
    if message.entities and message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.MENTION]):
        entities = message.parse_entities([MessageEntity.TEXT_MENTION, MessageEntity.MENTION])
        for ent in entities:
            if ent.type == MessageEntity.TEXT_MENTION:
                user_id = ent.user.id
                fst_name = ent.user.first_name

            elif ent.type == MessageEntity.MENTION:
                user_id = get_user_id(message.text[ent.offset:ent.offset + ent.length])
                if not user_id:
                    # Should never happen, since for a user to become AFK they must have spoken. Maybe changed username?
                    return
                try:
                    chat = bot.get_chat(user_id)
                except BadRequest:
                    print("Error: Could not fetch userid {} for AFK module".format(user_id))
                    return
                fst_name = chat.first_name

            else:
                return

            check_afk(bot, update, user_id, fst_name)

    elif message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        fst_name = message.reply_to_message.from_user.first_name
        check_afk(bot, update, user_id, fst_name)


def check_afk(bot, update, user_id, fst_name):
    if sql.is_afk(user_id):
        user = sql.check_afk_status(user_id)
        if not user.reason:
            res = "{} is AFK!".format(fst_name)
        else:
            res = "{} is AFK!.\nReason: <code>{}</code>".format(html.escape(fst_name), html.escape(user.reason))
        update.effective_message.reply_text(res, parse_mode=ParseMode.HTML)


def __user_info__(user_id):
    is_afk = sql.is_afk(user_id)

    text = "<b>Currently AFK</b>: {}"
    if is_afk:
        return text.format("Yes")

    else:
        return text.format("No")


def __gdpr__(user_id):
    sql.rm_afk(user_id)

__help__ = """
 - /afk <reason>: mark yourself as AFK.
 - brb <reason>: same as the afk command - but not a command.
When marked as AFK, any mentions will be replied to with a message to say that you're not available!
"""

__mod_name__ = "AFK"

AFK_HANDLER = DisableAbleCommandHandler("afk", afk)
AFK_REGEX_HANDLER = DisableAbleRegexHandler("(?i)brb", afk, friendly="afk")
NO_AFK_HANDLER = MessageHandler(Filters.all & Filters.group, no_longer_afk)
AFK_REPLY_HANDLER = MessageHandler(Filters.all & Filters.group, reply_afk)

dispatcher.add_handler(AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REGEX_HANDLER, AFK_GROUP)
dispatcher.add_handler(NO_AFK_HANDLER, AFK_GROUP)
dispatcher.add_handler(AFK_REPLY_HANDLER, AFK_REPLY_GROUP)
