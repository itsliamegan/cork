from dataclasses import dataclass

from helios.view import Component

from app.data import Board, Pin, User


@dataclass
class PinDetails(Component):
	template = "pins.details"

	pin: Pin
	boards: list[Board]
	adder: User | None
	is_unfiled: bool
	new_tab: bool = False
