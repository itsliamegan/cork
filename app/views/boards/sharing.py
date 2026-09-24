from dataclasses import dataclass
from uuid import UUID

from helios.view import Component

from app.data import User


@dataclass
class BoardSharing(Component):
	template = "boards.sharing"

	owner: User
	users: list[User]
	shared_user_ids: set[UUID]
