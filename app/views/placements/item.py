from helios.view import Component

from app import Pin, Placement, User


class PlacementItem(Component):
	template = "placements.item"

	pin: Pin
	placement: Placement
	user: User
	can_remove: bool
