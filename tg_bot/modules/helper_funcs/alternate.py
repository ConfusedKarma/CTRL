from functools import wraps

from telegram import User, Chat, ChatMember
from telegram import error, ChatAction

from tg_bot import DEL_CMDS, SUDO_USERS, dispatcher


def send_message(message, text,  *args,**kwargs):
	try:
		return message.reply_text(text, *args,**kwargs)
	except error.BadRequest as err:
		if str(err) == "Reply message not found":
			return message.reply_text(text, quote=False, *args,**kwargs)
