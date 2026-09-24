from helios.view import Attributes, Component

from app.data import Board


class BoardChips(Component):
	template = "boards.chips"

	boards: list[Board]
	is_unfiled: bool
	attributes: Attributes = Attributes()
