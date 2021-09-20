from tg_bot import (
    Tclient,
    SUDO_USERS,
    WHITELIST_USERS
)

MOD_USERS = SUDO_USERS + WHITELIST_USERS

MOD_USERS = (
    list(SUDO_USERS)
    + list(WHITELIST_USERS)
)

MOD_USERS.append(1087968824)
