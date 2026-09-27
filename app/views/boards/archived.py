from helios.view import Component

from app import Archival, Pin, Placement, User


class ArchivedPin(Component):
	template = "boards.archived"

	archival: Archival
	placement: Placement
	pin: Pin
	user: User
	can_remove: bool
