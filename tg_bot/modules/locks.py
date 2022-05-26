from telethon.tl.functions.messages import EditChatDefaultBannedRightsRequest
from telethon.tl.types import ChatBannedRights

from telethon import TelegramClient, events, functions, types
from tg_bot.modules.helper_funcs.Tclient.chatstatus import user_is_admin
from tg_bot.modules.sql.locks_sql import update_lock, is_locked, get_locks
from tg_bot import Tclient


@Tclient.on(events.NewMessage(pattern="[/!]lock( (?P<target>\S+)|$)"))
async def lock(event):
    if event.sender_id is None:
        return

    input_str = event.pattern_match.group("target")
    peer_id = event.chat_id
    chat = await event.get_chat()

    if not event.is_group:
        return await event.reply("`I don't think this is a group.`")

    if not await user_is_admin(user_id=event.sender_id, message=event):
        await event.reply(peer_id, f"You need to admin to Lock this in {event.chat.title}")
        return

    msg = None
    media = None
    sticker = None
    gif = None
    gamee = None
    ainline = None
    gpoll = None
    adduser = None
    cpin = None
    changeinfo = None
    if input_str == "msg":
        msg = True
        what = "messages"
    elif input_str == "media":
        media = True
        what = "media"
    elif input_str == "sticker":
        sticker = True
        what = "stickers"
    elif input_str == "gif":
        gif = True
        what = "GIFs"
    elif input_str == "game":
        gamee = True
        what = "games"
    elif input_str == "inline":
        ainline = True
        what = "inline bots"
    elif input_str == "poll":
        gpoll = True
        what = "polls"
    elif input_str == "invite":
        adduser = True
        what = "invites"
    elif input_str == "pin":
        cpin = True
        what = "pins"
    elif input_str == "info":
        changeinfo = True
        what = "chat info"
    elif input_str == "all":
        msg = True
        media = True
        sticker = True
        gif = True
        gamee = True
        ainline = True
        gpoll = True
        adduser = True
        cpin = True
        changeinfo = True
        what = "everything"
    else:
        if not input_str:
            return await event.reply("`I can't lock nothing !!`")
        if input_str in (("url", "anonchannel", "forward", "commands")):
            update_lock(peer_id, input_str, True)
            return await event.reply(f"Locked `{input_str}` in **{event.chat.title}**.")

    lock_rights = ChatBannedRights(
        until_date=None,
        send_messages=msg,
        send_media=media,
        send_stickers=sticker,
        send_gifs=gif,
        send_games=gamee,
        send_inline=ainline,
        send_polls=gpoll,
        invite_users=adduser,
        pin_messages=cpin,
        change_info=changeinfo,
    )
    try:
        await event.client(
            EditChatDefaultBannedRightsRequest(peer=peer_id,
                                               banned_rights=lock_rights))
        await event.reply(f"Locked `{what}` in **{event.chat.title}**.")
    except BaseException as e:
        return await event.reply(
            f"`Do I have proper rights for that ??`\n**Error:** {str(e)}")
      

@Tclient.on(events.NewMessage(pattern="[/!]unlock( (?P<target>\S+)|$)"))
async def rem_locks(event):
    if event.sender_id is None:
        return

    if not event.is_group:
        return await event.reply("`I don't think this is a group.`")

    input_str = event.pattern_match.group("target")
    peer_id = event.chat_id
    chat = await event.get_chat()

    if not await user_is_admin(user_id=event.sender_id, message=event):
        return await event.reply(peer_id, f"You need to be a admin to Unlock it in {event.chat.title}")

    msg = None
    media = None
    sticker = None
    gif = None
    gamee = None
    ainline = None
    gpoll = None
    adduser = None
    cpin = None
    changeinfo = None
    if input_str == "msg":
        msg = False
        what = "messages"
    elif input_str == "media":
        media = False
        what = "media"
    elif input_str == "sticker":
        sticker = False
        what = "stickers"
    elif input_str == "gif":
        gif = False
        what = "GIFs"
    elif input_str == "game":
        gamee = False
        what = "games"
    elif input_str == "inline":
        ainline = False
        what = "inline bots"
    elif input_str == "poll":
        gpoll = False
        what = "polls"
    elif input_str == "invite":
        adduser = False
        what = "invites"
    elif input_str == "pin":
        cpin = False
        what = "pins"
    elif input_str == "info":
        changeinfo = False
        what = "chat info"
    elif input_str == "all":
        msg = False
        media = False
        sticker = False
        gif = False
        gamee = False
        ainline = False
        gpoll = False
        adduser = False
        cpin = False
        changeinfo = False
        what = "everything"
    else:
        if not input_str:
            return await event.reply("`I can't unlock nothing !!`")
        if input_str in (("url", "anonchannel", "forward", "commands")):
            update_lock(peer_id, input_str, False)
            return await event.reply(f"Unlocked `{input_str}` in **{event.chat.title}**.")

    unlock_rights = ChatBannedRights(
        until_date=None,
        send_messages=msg,
        send_media=media,
        send_stickers=sticker,
        send_gifs=gif,
        send_games=gamee,
        send_inline=ainline,
        send_polls=gpoll,
        invite_users=adduser,
        pin_messages=cpin,
        change_info=changeinfo,
    )
    try:
        await event.client(
            EditChatDefaultBannedRightsRequest(peer=peer_id,
                                               banned_rights=unlock_rights))
        await event.reply(f"Unlocked `{what}` in **{event.chat.title}**.")
    except BaseException as e:
        return await event.reply(
            f"`Do I have proper rights for that ??`\n**Error:** {str(e)}")
     
        
@Tclient.on(events.NewMessage(pattern="[/!]locks"))
async def _(event):
    if event.fwd_from:
        return
    if not event.is_group:
        return await event.reply("`I don't think this is a group.`")
    res = ""
    if current_db_locks := get_locks(event.chat_id):
        res = (
            "Following are the DataBase locks in this chat: \n"
            + "• `url`: `{}`\n".format(current_db_locks.url)
        )

        res += "• `anonchannel`: `{}`\n".format(current_db_locks.anonchannel)
        res += "• `forward`: `{}`\n".format(current_db_locks.forward)
        res += "• `commands`: `{}`\n".format(current_db_locks.commands)
    else:
        res = "There are no DataBase locks in this chat"
    current_chat = await event.get_chat()
    try:
        current_api_locks = current_chat.default_banned_rights
    except AttributeError as e:
        LOGGER.info(str(e))
    else:
        res += "\nFollowing are the API locks in this chat: \n"
        res += "• `msg`: `{}`\n".format(current_api_locks.send_messages)
        res += "• `media`: `{}`\n".format(current_api_locks.send_media)
        res += "• `sticker`: `{}`\n".format(current_api_locks.send_stickers)
        res += "• `gif`: `{}`\n".format(current_api_locks.send_gifs)
        res += "• `game`: `{}`\n".format(current_api_locks.send_games)
        res += "• `inline bots`: `{}`\n".format(current_api_locks.send_inline)
        res += "• `poll`: `{}`\n".format(current_api_locks.send_polls)
        res += "• `invite`: `{}`\n".format(current_api_locks.invite_users)
        res += "• `pin`: `{}`\n".format(current_api_locks.pin_messages)
        res += "• `info`: `{}`\n".format(current_api_locks.change_info)
    await event.reply(res)
    
    
@Tclient.on(events.MessageEdited())  # pylint:disable=E0602
@Tclient.on(events.NewMessage())  # pylint:disable=E0602
async def check_incoming_messages(event):
    # TODO: exempt admins from locks
    peer_id = event.chat_id
    result = await event.client(functions.channels.GetFullChannelRequest(event.sender.id))
    # print(result.full_chat.linked_chat_id)
    if is_locked(peer_id, "anonchannel"):
        if event.chat.id == result.full_chat.linked_chat_id:
            return # whitelist linked channel to talk in chat
        if event.sender.left:
            try:
                await event.delete()
            except Exception as e:
                await event.reply(
                    "I don't seem to have ADMIN permission here. \n`{}`".format(str(e))
                )
                update_lock(peer_id, "anonchannel", False)
    if await user_is_admin(user_id=event.sender_id, message=event):
        return
    if is_locked(peer_id, "forward") and event.fwd_from:
        try:
            await event.delete()
        except Exception as e:
            await event.reply(
                "I don't seem to have ADMIN permission here. \n`{}`".format(str(e))
            )
            update_lock(peer_id, "forward", False)
    if is_locked(peer_id, "url"):
        is_url = False
        if entities := event.message.entities:
            for entity in entities:
                if isinstance(entity, (types.MessageEntityTextUrl, types.MessageEntityUrl)):
                    is_url = True
        if is_url:
            try:
                await event.delete()
            except Exception as e:
                await event.reply(
                    "I don't seem to have ADMIN permission here. \n`{}`".format(str(e))
                )
                update_lock(peer_id, "url", False)
    if is_locked(peer_id, "commands"):
        is_command = False
        if entities := event.message.entities:
            for entity in entities:
                if isinstance(entity, types.MessageEntityBotCommand):
                    is_command = True
        if is_command:
            try:
                await event.delete()
            except Exception as e:
                await event.reply(
                    "I don't seem to have ADMIN permission here. \n`{}`".format(str(e))
                )
                update_lock(peer_id, "commands", False)
                
                
__help__ = """
*Admins only:*
• /lock <type> : to lock that.
• /unlock <type> : to unlock that.

example: 
• /lock all: Lock everything.
• /locks to check locked items.
locks types below that can be lockable and unlockable.
   `Invite`
   `anonchannel`
   `gif`
   `pin`
   `info`
   `inline bots`
   `sticker`
   `game`
   `poll`
   `media`
   `msg`
   `forward`
   `url`
   `commands`
"""

__mod_name__ = "Locks"
