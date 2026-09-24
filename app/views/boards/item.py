from helios.view import Component

from app.data import Board, User


class BoardItem(Component):
	template = "boards.item"

	board: Board
	user: User

	@property
	def owned(self) -> bool:
		return self.board.creator_id == self.user.id
