from psutil import cpu_percent, virtual_memory, disk_usage
from pyrogram.filters import command, regex
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from time import time

from bot import (
    task_dict_lock,
    status_dict,
    task_dict,
    botStartTime,
    DOWNLOAD_DIR,
    intervals,
    bot,
)
from ..helper.ext_utils.bot_utils import sync_to_async, new_task
from ..helper.ext_utils.status_utils import (
    MirrorStatus,
    get_readable_file_size,
    get_readable_time,
    speed_string_to_bytes,
)
from ..helper.telegram_helper.bot_commands import BotCommands
from ..helper.telegram_helper.filters import CustomFilters
from ..helper.telegram_helper.message_utils import (
    send_message,
    delete_message,
    auto_delete_message,
    send_status_message,
    update_status_message,
    edit_message,
)
from ..helper.telegram_helper.button_build import ButtonMaker


@new_task
async def mirror_status(_, message):
    async with task_dict_lock:
        count = len(task_dict)
    if count == 0:
        currentTime = get_readable_time(time() - botStartTime)
        free = get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)
        msg = f"No Active Tasks!\nEach user can get status for his tasks by adding me or user_id after cmd: /{BotCommands.StatusCommand} me"
        msg += (
            f"\n<b>CPU:</b> {cpu_percent()}% | <b>FREE:</b> {free}"
            f"\n<b>RAM:</b> {virtual_memory().percent}% | <b>UPTIME:</b> {currentTime}"
        )
        reply_message = await send_message(message, msg)
        await auto_delete_message(message, reply_message)
    else:
        text = message.text.split()
        if len(text) > 1:
            user_id = message.from_user.id if text[1] == "me" else int(text[1])
        else:
            user_id = 0
            sid = message.chat.id
            if obj := intervals["status"].get(sid):
                obj.cancel()
                del intervals["status"][sid]
        await send_status_message(message, user_id)
        await delete_message(message)


@new_task
async def status_pages(_, query):
    data = query.data.split()
    key = int(data[1])
    if data[2] == "ref":
        await query.answer()
        await update_status_message(key, force=True)
    elif data[2] in ["nex", "pre"]:
        await query.answer()
        async with task_dict_lock:
            if data[2] == "nex":
                status_dict[key]["page_no"] += status_dict[key]["page_step"]
            else:
                status_dict[key]["page_no"] -= status_dict[key]["page_step"]
    elif data[2] == "ps":
        await query.answer()
        async with task_dict_lock:
            status_dict[key]["page_step"] = int(data[3])
    elif data[2] == "st":
        await query.answer()
        async with task_dict_lock:
            status_dict[key]["status"] = data[3]
        await update_status_message(key, force=True)


bot.add_handler(
    MessageHandler(
        mirror_status,
        filters=command(BotCommands.StatusCommand, case_sensitive=True)
        & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(status_pages, filters=regex("^status")))
