import time

import requests
from telegram import Update, Bot
from telegram import ParseMode

from tg_bot.modules.disable import DisableAbleCommandHandler
from tg_bot import dispatcher
from telegram.ext import run_async


@run_async
def ping(bot: Bot, update: Update):
    start_time = time.time()
    requests.get('https://api.telegram.org')
    end_time = time.time()
    ms = float(end_time - start_time)
    update.effective_message.reply_text("🏓 Pong!\n⏱️Reply took: {0:.2f}s".format(round(ms, 2) % 60), parse_mode=ParseMode.MARKDOWN)


__mod_name__ = "Ping"

PING_HANDLER = DisableAbleCommandHandler("ping", ping)

dispatcher.add_handler(PING_HANDLER)
