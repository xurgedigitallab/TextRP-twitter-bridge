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

from typing import Any
import asyncio

from mautrix.bridge import Bridge
from mautrix.types import RoomID, UserID
from mautrix.util import background_task

from . import commands
from .backfill import BackfillStatus
from .config import Config
from .db import init as init_db, upgrade_table
from .matrix import MatrixHandler
from .portal import Portal
from .puppet import Puppet
from .user import User
from .version import linkified_version, version
from .web import ProvisioningAPI


class TwitterBridge(Bridge):
    module = "mautrix_twitter"
    name = "mautrix-twitter"
    beeper_service_name = "twitter"
    beeper_network_name = "twitter"
    command = "python -m mautrix-twitter"
    description = "A Matrix-Twitter DM puppeting bridge."
    repo_url = "https://github.com/mautrix/twitter"
    version = version
    markdown_version = linkified_version
    config_class = Config
    matrix_class = MatrixHandler
    upgrade_table = upgrade_table

    matrix: MatrixHandler
    config: Config
    provisioning_api: ProvisioningAPI

    def prepare_db(self) -> None:
        super().prepare_db()
        init_db(self.db)

    def prepare_bridge(self) -> None:
        super().prepare_bridge()
        cfg = self.config["appservice.provisioning"]
        self.provisioning_api = ProvisioningAPI(cfg["shared_secret"])
        self.az.app.add_subapp(cfg["prefix"], self.provisioning_api.app)

    async def start(self) -> None:
        self.add_startup_actions(User.init_cls(self))
        self.add_startup_actions(Puppet.init_cls(self))
        Portal.init_cls(self)
        if self.config["bridge.resend_bridge_info"]:
            self.add_startup_actions(self.resend_bridge_info())
        background_task.create(BackfillStatus.backfill_loop())
        await super().start()

    def prepare_stop(self) -> None:
        self.add_shutdown_actions(user.stop() for user in User.by_twid.values())
        for puppet in Puppet.by_custom_mxid.values():
            puppet.stop()

    async def resend_bridge_info(self) -> None:
        self.config["bridge.resend_bridge_info"] = False
        self.config.save()
        self.log.info("Re-sending bridge info state event to all portals")
        async for portal in Portal.all_with_room():
            await portal.update_bridge_info()
        self.log.info("Finished re-sending bridge info state events")

    async def get_user(self, user_id: UserID, create: bool = True) -> User:
        return await User.get_by_mxid(user_id, create=create)

    async def get_portal(self, room_id: RoomID) -> Portal:
        return await Portal.get_by_mxid(room_id)

    async def get_puppet(self, user_id: UserID, create: bool = False) -> Puppet:
        return await Puppet.get_by_mxid(user_id, create=create)

    async def get_double_puppet(self, user_id: UserID) -> Puppet:
        return await Puppet.get_by_custom_mxid(user_id)

    def is_bridge_ghost(self, user_id: UserID) -> bool:
        return bool(Puppet.get_id_from_mxid(user_id))

    async def count_logged_in_users(self) -> int:
        return len([user for user in User.by_twid.values() if user.twid])

    async def manhole_global_namespace(self, user_id: UserID) -> dict[str, Any]:
        return {
            **await super().manhole_global_namespace(user_id),
            "User": User,
            "Portal": Portal,
            "Puppet": Puppet,
        }


TwitterBridge().run()
