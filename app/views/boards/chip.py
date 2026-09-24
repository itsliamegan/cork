from dataclasses import dataclass

from helios.view import Component

from app.data import Board


@dataclass
class BoardChip(Component):
	template = "boards.chip"

	board: Board
