from dataclasses import dataclass
from uuid import UUID

from helios.view import Component

from app.data import Board, User


@dataclass
class BoardOption:
	board: Board
	shared_with: list[User]


@dataclass
class PinPlacements(Component):
	template = "pins.placements"

	options: list[BoardOption]
	selected_board_ids: set[UUID]
