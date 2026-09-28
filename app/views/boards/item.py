from helios.view import Component

from app import Access, Board


class BoardItem(Component):
	template = "boards.item"

	board: Board
	access: Access
