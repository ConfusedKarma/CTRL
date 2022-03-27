import requests, os
from time import sleep

from tg_bot import Tclient
from bs4 import BeautifulSoup
from telethon import events

from tg_bot.modules.helper_funcs.Tclient.chatstatus import user_is_admin, can_ban_users

@Tclient.on(events.NewMessage(pattern="[/!]paste"))
async def paste_bin(event):
    if not event.reply_to:
        return await event.reply("Reply /paste Message|File")
    r = await event.get_reply_message()

    if not r.media and not r.message:
        return await event.reply("Is replied msg is text or file?")

    if r.message:
        content = str(r.message)
    else:
        doc = await Tclient.download_media(r)
        with open(doc, mode="r") as f:
            content = f.read()
        os.remove(doc)
    res = requests.post("https://pastefy.ga/api/v2/paste",
                        data={"content":content,"title":"","encrypted":"false","type":"PASTE"})
    key = res.json()["paste"]["id"]
    msg = f"**Pastefy** : https://pastefy.ga/{key}"
    await event.reply(msg, parse_mode="markdown")
    
    
@Tclient.on(events.NewMessage(pattern="[/!]trt"))
async def trans(event):
    if not event.reply_to:
        return await event.reply("Reply /trt {code}")
    r = await event.get_reply_message()
    co = event.message.message[len("/trt "):]
    try:
        re = requests.get(f"https://translate.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={co}&q={r.message}")
        res = re.json()
        lang = res["src"]
        result = res["sentences"]
        for x in result:
            content = (x["trans"])
        msg = f"""
**Text**: `{r.message}`
Translated from **{lang}** to **{co}**
`{content}`
"""
        await event.reply(msg, parse_mode="markdown")
    except KeyError: # TODO: ARABIC AND HINDI
        msg = "Failed to translate"
        await event.reply(msg, parse_mode="markdown")


@Tclient.on(events.NewMessage(pattern="[/!]bin"))
async def bin(event):
    BIN = event.message.message[len("/bin "):11]
    r = requests.get(f"https://bins.ws/search?bins={BIN}&bank=&country=").text
    soup = BeautifulSoup(r, features="html.parser")
    k = soup.find("div", {"class": "page"})
    await event.reply(f"**{k.get_text()[62:]}**", parse_mode="markdown")
    


@Tclient.on(events.NewMessage(pattern="[.?]ban"))
async def ban(event):
    chat = await event.get_chat()
    admin = chat.admin_rights
    creator = chat.creator

    # Well
    if not admin and not creator:
        await event.reply("You aren't Admin!")
        return

    if not event.is_group:
        await event.reply("I don't think this is a group.")
        return

    if not await user_is_admin(user_id=event.sender_id, message=event):
        await event.reply("Only Admins are allowed to use this command")
        return

    if not await can_ban_users(message=event):
        await event.reply("Don't have enough permission :(")
        return

    user = await event.user()
    if not user:
        await event.reply(
            "Reply to user message or Mention else specify a valid ID!"
        )
    await Tclient.edit_permissions(event.chat_id, user.id, view_messages=False)
    await event.reply(f"`{str(user.id)}` was banned!")


__help__ = """
 - /paste: Paste on pastefy.
 - /trt: translate.
 - /bin: get 6 digit bank identify number.
"""

__mod_name__ = "Ctrl"
