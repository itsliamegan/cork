from dataclasses import dataclass

from helios.view import Component

from app import Board, User


@dataclass
class PlacementOption:
	board: Board
	others: list[User]


class PinPlacements(Component):
	template = "pins.placements"

	options: list[PlacementOption]
	selected_board_ids: set[str]
