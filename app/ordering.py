from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store

from app.board import Board
from app.move import Move
from app.share import Share

if TYPE_CHECKING:
	from app.access import Access


class Ordering(Model):
	table = "orderings"

	user_id: UUID
	board_id: UUID
	position: int

	@classmethod
	def arrange(
		cls,
		store: Store,
		access: Access,
	) -> tuple[list[Board], list[Board]]:
		boards = access.find_boards()
		shares_by_board_id: dict[UUID, list[Share]] = {}
		for share in (
			store.query(Share).where_in(board_id=[board.id for board in boards]).all()
		):
			shares_by_board_id.setdefault(share.board_id, []).append(share)
		positions = {
			ordering.board_id: ordering.position
			for ordering in store.find_by(cls, user_id=access.user.id)
		}

		private: list[Board] = []
		shared: list[Board] = []
		entered_at: dict[UUID, datetime] = {}
		for board in boards:
			shares = shares_by_board_id.get(board.id, [])
			if not shares:
				private.append(board)
				entered_at[board.id] = board.created_at
			elif access.owns(board):
				shared.append(board)
				entered_at[board.id] = min(share.created_at for share in shares)
			else:
				shared.append(board)
				entered_at[board.id] = next(
					share.created_at
					for share in shares
					if share.user_id == access.user.id
				)

		def arranged(section: list[Board]) -> list[Board]:
			section.sort(key=lambda board: board.id)
			section.sort(key=lambda board: entered_at[board.id], reverse=True)
			section.sort(
				key=lambda board: (board.id in positions, positions.get(board.id, 0))
			)
			return section

		return arranged(private), arranged(shared)

	@classmethod
	def move(cls, store: Store, access: Access, move: Move):
		private, shared = cls.arrange(store, access)
		private_ids = [board.id for board in private]
		shared_ids = [board.id for board in shared]
		if move.record_id in private_ids:
			order = move.apply(private_ids)
		else:
			order = move.apply(shared_ids)
		if order is None:
			return

		accessible_board_ids = {*private_ids, *shared_ids}
		orderings = {}
		for ordering in store.find_by(cls, user_id=access.user.id):
			if ordering.board_id in accessible_board_ids:
				orderings[ordering.board_id] = ordering
			else:
				store.delete(ordering)
		for position, board_id in enumerate(order):
			ordering = orderings.get(board_id)
			if ordering is None:
				store.create(
					cls,
					user_id=access.user.id,
					board_id=board_id,
					position=position,
				)
			else:
				store.update(ordering, position=position)
