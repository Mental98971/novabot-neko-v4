"""
Shared economy data-access helpers.

Factored out of bot/plugins/economy.py so bot/plugins/games.py (betting
commands) can transact coins through the same functions instead of
duplicating balance-check-and-deduct logic in two places.
"""
from __future__ import annotations

import math

from sqlalchemy import select

from bot.config import settings
from bot.core.database import ChatMember, async_session


def level_from_xp(xp: int) -> int:
    return int(math.sqrt(max(0, xp) / 100))


def xp_for_level(level: int) -> int:
    return 100 * (level ** 2)


async def get_or_create_member(session, chat_id: int, user_id: int) -> ChatMember:
    result = await session.execute(
        select(ChatMember).where(ChatMember.chat_id == chat_id, ChatMember.user_id == user_id)
    )
    member = result.scalar_one_or_none()
    if member is None:
        member = ChatMember(chat_id=chat_id, user_id=user_id, coins=settings.economy_starting_balance)
        session.add(member)
        await session.flush()
    return member


async def get_balance(chat_id: int, user_id: int) -> int:
    async with async_session() as session:
        member = await get_or_create_member(session, chat_id, user_id)
        balance = member.coins or 0
        await session.commit()
        return balance


async def try_spend(chat_id: int, user_id: int, amount: int) -> bool:
    """Atomically deduct `amount` coins if the balance covers it.
    Returns whether the deduction happened."""
    async with async_session() as session:
        member = await get_or_create_member(session, chat_id, user_id)
        if (member.coins or 0) < amount:
            await session.commit()
            return False
        member.coins -= amount
        await session.commit()
        return True


async def add_coins(chat_id: int, user_id: int, amount: int) -> int:
    """Add (or, with a negative amount, remove) coins. Returns new balance."""
    async with async_session() as session:
        member = await get_or_create_member(session, chat_id, user_id)
        member.coins = max(0, (member.coins or 0) + amount)
        new_balance = member.coins
        await session.commit()
        return new_balance


async def add_xp(chat_id: int, user_id: int, amount: int) -> tuple[int, bool]:
    """Add XP. Returns (new_level, did_level_up)."""
    async with async_session() as session:
        member = await get_or_create_member(session, chat_id, user_id)
        old_level = level_from_xp(member.xp or 0)
        member.xp = (member.xp or 0) + amount
        new_level = level_from_xp(member.xp)
        member.level = new_level
        await session.commit()
        return new_level, new_level > old_level
