from helios.view import Component

from app.data import Board


class BoardChip(Component):
	template = "boards.chip"

	board: Board
