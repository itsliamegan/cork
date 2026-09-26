from uuid import UUID

from helios.database import Model, Store

from app.board import Board
from app.user import User


class Share(Model):
	table = "shares"

	board_id: UUID
	user_id: UUID

	@classmethod
	def exists(cls, store: Store, board: Board, user: User) -> bool:
		share = store.query(cls).where(board_id=board.id, user_id=user.id).first()
		return share is not None

	@classmethod
	def find_board_ids(cls, store: Store, user: User) -> list[UUID]:
		return [share.board_id for share in store.find_by(cls, user_id=user.id)]

	@classmethod
	def find_boards(cls, store: Store, user: User) -> list[Board]:
		board_ids = cls.find_board_ids(store, user)
		return store.query(Board).where_in(id=board_ids).all()

	@classmethod
	def replace(cls, store: Store, board: Board, users: list[User]) -> None:
		user_ids = {user.id for user in users}
		if board.creator_id in user_ids:
			raise ValueError(f"Board {board.id} cannot be shared with its creator")

		shares = store.find_by(cls, board_id=board.id)
		for share in shares:
			if share.user_id not in user_ids:
				store.delete(share)
		shared_user_ids = {share.user_id for share in shares}
		for user in users:
			if user.id not in shared_user_ids:
				store.create(cls, board_id=board.id, user_id=user.id)
				shared_user_ids.add(user.id)
