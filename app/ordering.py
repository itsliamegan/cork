from uuid import UUID

from helios.database import Model, Store

from app.board import Board
from app.user import User


class Ordering(Model):
	table = "orderings"

	user_id: UUID
	board_id: UUID
	position: int

	@classmethod
	def arrange(cls, store: Store, user: User, boards: list[Board]) -> list[Board]:
		board_ids = {board.id for board in boards}
		positions = {}
		for ordering in store.find_by(cls, user_id=user.id):
			if ordering.board_id not in board_ids:
				continue
			position = positions.get(ordering.board_id)
			if position is None or ordering.position < position:
				positions[ordering.board_id] = ordering.position

		unpositioned = sorted(
			(board for board in boards if board.id not in positions),
			key=lambda board: (board.created_at is not None, board.created_at),
			reverse=True,
		)
		positioned = sorted(
			(board for board in boards if board.id in positions),
			key=lambda board: (board.created_at is not None, board.created_at),
			reverse=True,
		)
		positioned.sort(key=lambda board: positions[board.id])

		return [*unpositioned, *positioned]
