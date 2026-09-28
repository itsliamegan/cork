from helios.view import Component

from app import Pin, Placement, User


class PlacementMenu(Component):
	template = "placements.menu"

	pin: Pin
	placement: Placement
	user: User
	can_remove: bool
