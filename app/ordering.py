from datetime import datetime
from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Model, Store, attr

from app.board import Board
from app.user import User


class Ordering(Model):
	table = "orderings"

	user_id = attr(UUID)
	board_id = attr(UUID)
	position = attr(int)

	@classmethod
	def arrange(cls, ctx: Context, boards: list[Board]) -> list[Board]:
		store = ctx.get(Store)
		auth = ctx.get(Authenticator)
		user = cast(User, auth.user)

		def created_at(board: Board) -> datetime:
			if board.created_at is None:
				raise ValueError("cannot order an unsaved board")
			return board.created_at

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
			key=created_at,
			reverse=True,
		)
		positioned = sorted(
			(board for board in boards if board.id in positions),
			key=created_at,
			reverse=True,
		)
		positioned.sort(key=lambda board: positions[board.id])

		return [*unpositioned, *positioned]
