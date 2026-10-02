from uuid import UUID

from helios.database import Model, Store, belongs_to

from app.board import Board
from app.user import User


class Share(Model):
	table = "shares"

	board_id: UUID
	user_id: UUID
	user: User = belongs_to("user_id")

	@classmethod
	def replace(cls, store: Store, board: Board, users: list[User]) -> None:
		user_ids = {user.id for user in users}
		if board.creator_id in user_ids:
			raise ValueError(f"Board {board.id} cannot be shared with its creator")

		store.load(board, "shares")
		shares = board.shares
		was_shared = len(shares) > 0
		for share in shares:
			if share.user_id not in user_ids:
				store.delete(share)
		shared_user_ids = {share.user_id for share in shares}
		for user in users:
			if user.id not in shared_user_ids:
				store.create(cls, board_id=board.id, user_id=user.id)
				shared_user_ids.add(user.id)

		is_shared = len(user_ids) > 0
		if was_shared != is_shared:
			from app.ordering import Ordering

			for ordering in store.find_by(
				Ordering,
				user_id=board.creator_id,
				board_id=board.id,
			):
				store.delete(ordering)
