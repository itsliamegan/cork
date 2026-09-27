from helios.view import Component

from app import Pin, Placement, User


class PinMenu(Component):
	template = "pins.menu"

	pin: Pin
	placement: Placement
	user: User
	can_remove: bool
