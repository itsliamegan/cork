from dataclasses import dataclass

from helios.view import Component

from app.data import User


@dataclass
class SharingPerson:
	user: User
	has_access: bool


@dataclass
class BoardSharing(Component):
	template = "boards.sharing"

	owner: User
	people: list[SharingPerson]
