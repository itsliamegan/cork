from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store

from app.board import Board

if TYPE_CHECKING:
	from app.access import Access


class Ordering(Model):
	table = "orderings"

	user_id: UUID
	board_id: UUID
	position: int

	@classmethod
	def arrange(cls, store: Store, access: Access) -> list[Board]:
		boards = access.find_boards()
		positions = {
			ordering.board_id: ordering.position
			for ordering in store.find_by(cls, user_id=access.user.id)
		}

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

	@classmethod
	def replace(cls, store: Store, access: Access, boards: list[Board]) -> None:
		board_ids = [board.id for board in boards]
		if len(set(board_ids)) != len(board_ids):
			raise ValueError("Boards must be ordered once each")
		inaccessible_board_ids = set(board_ids) - set(access.find_board_ids())
		if inaccessible_board_ids:
			raise ValueError(f"Boards {inaccessible_board_ids} are not accessible")

		for ordering in store.find_by(cls, user_id=access.user.id):
			store.delete(ordering)
		for position, board in enumerate(boards):
			store.create(
				cls,
				user_id=access.user.id,
				board_id=board.id,
				position=position,
			)
