from helios.view import Component

from app import Archival, Pin, Placement, User


class ArchivalItem(Component):
	template = "archivals.item"

	archival: Archival
	pin: Pin
	placement: Placement
	user: User
	can_remove: bool
