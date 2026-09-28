from helios.view import Component

from app import Board, Pin, Preferences, User


class PinDetails(Component):
	template = "pins.details"

	pin: Pin
	boards: list[Board]
	adder: User | None
	is_unfiled: bool
	preferences: Preferences
