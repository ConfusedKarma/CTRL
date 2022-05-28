import requests, os

from tg_bot import Tclient
from bs4 import BeautifulSoup
from telethon import events

@Tclient.on(events.NewMessage(pattern="[/!]paste"))
async def paste_bin(event):
    if not event.reply_to:
        return await event.reply("Reply /paste Message|File")
    r = await event.get_reply_message()
    
    if not r.media and not r.message:
        return await event.reply("Is replied msg is text or file?")

    if r.message:
        content = str(r.message)
    elif r.media:
        doc = await Tclient.download_media(r)
        with open(doc, mode="r") as f:
            content = f.read()
        os.remove(doc)
    res = requests.post("https://paste.centos.org/",
                        data={"code":content,"lang":"text","expire":259200,"submit":"submit"})
    # this paste will get deleted in 5months change expire to increase or decrese time.
    msg = f"**Paste** : {res.url}"
    await event.reply(msg, parse_mode="markdown")
    
    
@Tclient.on(events.NewMessage(pattern="[/!]trt"))
async def trans(event):
    if not event.reply_to:
        return await event.reply("Reply /trt {code}")
    r = await event.get_reply_message()
    co = event.message.message[len("/trt "):]
    try:
        re = requests.get(f"https://translate.google.com/translate_a/t?client=dict-chrome-ex&sl=auto&tl={co}&q={r.message}")
        res = re.text
        result = res.strip('[""]')
        so = result[-2:]
        msg = f"""
**INPUT**: `{r.message}`
Translated from **{so}** to **{co}**
`{result[:-5]}`
"""
        await event.reply(msg, parse_mode="markdown")
    except Exception as e:
        msg = f"Failed to translate: {e}"
        await event.reply(msg, parse_mode="markdown")


@Tclient.on(events.NewMessage(pattern="[/!]bin"))
async def bin(event):
    BIN = event.message.message[len("/bin "):11]
    r = requests.get(f"https://bins.ws/search?bins={BIN}&bank=&country=").text
    soup = BeautifulSoup(r, features="html.parser")
    k = soup.find("div", {"class": "page"})
    await event.reply(f"**{k.get_text()[62:]}**", parse_mode="markdown")
    

__help__ = """
 - /paste: Paste on paste centos for 5months.
 - /trt: translate.
 - /bin: get 6 digit bank identify number.
"""

__mod_name__ = "Ctrl"
