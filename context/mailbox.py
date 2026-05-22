"""Mailbox context — mirrors src/context/mailbox.tsx."""
from __future__ import annotations

from typing import Optional

from ..utils.mailbox import Mailbox


class MailboxContext(Mailbox):
    """Mailbox context backed by the shared Mailbox utility."""


_mailbox_instance: Optional[MailboxContext] = None


def MailboxProvider() -> MailboxContext:
    return useMailbox()


def useMailbox() -> MailboxContext:
    global _mailbox_instance
    if _mailbox_instance is None:
        _mailbox_instance = MailboxContext()
    return _mailbox_instance


use_mailbox = useMailbox
