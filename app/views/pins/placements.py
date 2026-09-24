from dataclasses import dataclass
from uuid import UUID

from helios.view import Component

from app.data import Board, User


@dataclass
class PlacementOption:
	board: Board
	others: list[User]


@dataclass
class PinPlacements(Component):
	template = "pins.placements"

	options: list[PlacementOption]
	selected_board_ids: set[UUID]
