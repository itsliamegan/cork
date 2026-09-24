from helios.view import Component

from app import Board


class BoardChip(Component):
	template = "boards.chip"

	board: Board
