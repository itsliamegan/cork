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
