from uuid import UUID

from helios.view import Component

from app import User


class BoardSharing(Component):
	template = "boards.sharing"

	owner: User
	users: list[User]
	shared_user_ids: set[UUID]
