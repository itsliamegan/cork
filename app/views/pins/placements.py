from dataclasses import dataclass
from uuid import UUID

from helios.view import Component

from app.data import Board


@dataclass
class PinPlacements(Component):
	template = "pins.placements"

	options: list[dict[str, Board | str]]
	selected_board_ids: set[UUID]
