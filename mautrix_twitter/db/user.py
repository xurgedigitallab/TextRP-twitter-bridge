# mautrix-twitter - A Matrix-Twitter DM puppeting bridge
# Copyright (C) 2022 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from attr import dataclass

from mautrix.types import RoomID, UserID
from mautrix.util.async_db import Database

fake_db = Database.create("") if TYPE_CHECKING else None


@dataclass
class User:
    db: ClassVar[Database] = fake_db

    mxid: UserID
    twid: int | None
    auth_token: str | None
    csrf_token: str | None
    poll_cursor: str | None
    notice_room: RoomID | None

    @property
    def _values(self):
        return (
            self.mxid,
            self.twid,
            self.auth_token,
            self.csrf_token,
            self.poll_cursor,
            self.notice_room,
        )

    async def insert(self) -> None:
        q = (
            'INSERT INTO "user" (mxid, twid, auth_token, csrf_token, poll_cursor, notice_room) '
            "VALUES ($1, $2, $3, $4, $5, $6)"
        )
        await self.db.execute(q, *self._values)

    async def update(self) -> None:
        q = (
            'UPDATE "user" SET twid=$2, auth_token=$3, csrf_token=$4,'
            "                  poll_cursor=$5, notice_room=$6 "
            "WHERE mxid=$1"
        )
        await self.db.execute(q, *self._values)

    @classmethod
    async def get_by_mxid(cls, mxid: UserID) -> User | None:
        q = (
            "SELECT mxid, twid, auth_token, csrf_token, poll_cursor, notice_room "
            'FROM "user" WHERE mxid=$1'
        )
        row = await cls.db.fetchrow(q, mxid)
        if not row:
            return None
        return cls(**row)

    @classmethod
    async def get_by_twid(cls, twid: int) -> User | None:
        q = (
            "SELECT mxid, twid, auth_token, csrf_token, poll_cursor, notice_room "
            'FROM "user" WHERE twid=$1'
        )
        row = await cls.db.fetchrow(q, twid)
        if not row:
            return None
        return cls(**row)

    @classmethod
    async def all_logged_in(cls) -> list[User]:
        q = (
            "SELECT mxid, twid, auth_token, csrf_token, poll_cursor, notice_room "
            'FROM "user" WHERE twid IS NOT NULL AND auth_token IS NOT NULL'
        )
        rows = await cls.db.fetch(q)
        return [cls(**row) for row in rows]
