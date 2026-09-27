from typing import Any

from helios.view import Component

from app import User


class PinList(Component):
	template = "boards.pins"

	rows: list[dict[str, Any]]
	user: User
	has_archived_pins: bool
