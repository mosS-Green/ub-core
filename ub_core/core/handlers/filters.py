from pyrogram.enums import ChatType
from pyrogram.filters import create
from pyrogram.types import Message

from ub_core import Config
from ub_core.core.conversation import Conversation

# Conversation Filter to check for incoming messages.
convo_filter = create(
    lambda _, __, message: (message.chat.id in Conversation.CONVO_DICT.keys())
    and (not message.reactions)
)


def client_check(_, client, message):
    if message.chat and message.chat.type == ChatType.PRIVATE:
        if Config.MODE == "bot" and client.is_user:
            return False
        return True
    if Config.MODE == "bot":
        return client.is_bot
    return True


def cmd_check(message: Message, trigger: str, sudo: bool = False) -> bool:
    """
    Check if first word of message is a valid cmd \n
    if sudo: check if sudo users have access to the cmd.
    """
    start_str = message.text.split(maxsplit=1)[0]
    cmd = start_str.replace(trigger, "", 1)
    cmd_obj = Config.CMD_DICT.get(cmd)
    if not cmd_obj:
        return False
    if sudo:
        in_loaded = cmd_obj.loaded
        has_access = cmd_obj.sudo
        return in_loaded and has_access
    return True


def basic_check(message: Message):
    return message.reactions or not message.text or not message.from_user


def owner_check(_, __, message: Message) -> bool:
    """Check if Message is from the Owner"""
    if (
        basic_check(message)
        or not message.text.startswith(Config.CMD_TRIGGER)
        or message.from_user.id != Config.OWNER_ID
        or (message.chat.id != Config.OWNER_ID and not message.outgoing)
    ):
        return False
    return cmd_check(message, Config.CMD_TRIGGER)


def sudo_check(_, __, message: Message) -> bool:
    """Check if Message is from a Sudo User"""
    if (
        not Config.SUDO
        or basic_check(message)
        or not message.text.startswith(Config.SUDO_TRIGGER)
        or message.from_user.id not in Config.SUDO_USERS
    ):
        return False
    return cmd_check(message, Config.SUDO_TRIGGER, sudo=True)


def super_user_check(_, client, message: Message):
    """Check if Message is from a Super User"""
    if (
        basic_check(message)
        or not message.text.startswith(Config.SUDO_TRIGGER)
        or (
            message.from_user.id not in Config.SUPERUSERS
            and (message.from_user.id == Config.OWNER_ID and client.is_user)
        )
        or message.from_user.id in Config.DISABLED_SUPERUSERS
    ):
        return False
    return cmd_check(message, Config.SUDO_TRIGGER)


cmd_filter = create(owner_check) | create(client_check) & (
    create(sudo_check) | create(super_user_check)
)
