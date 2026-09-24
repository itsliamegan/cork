from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Model, NotFoundError, Store, attr

from app.share import Share
from app.user import User


class Board(Model):
	table = "boards"

	title = attr(str)
	creator_id = attr(UUID)

	@classmethod
	def find_owned(cls, ctx: Context, id: UUID) -> Board:
		auth = ctx.get(Authenticator)
		user = cast(User, auth.user)
		board = ctx.get(Store).find_one(cls, id)
		if board.creator_id != user.id:
			raise NotFoundError(cls, id)
		return board

	@classmethod
	def find_accessible(cls, ctx: Context, id: UUID) -> Board:
		board = ctx.get(Store).find_one(cls, id)
		if not board.is_accessible(ctx):
			raise NotFoundError(cls, id)
		return board

	@classmethod
	def find_all_accessible(cls, ctx: Context) -> list[Board]:
		store = ctx.get(Store)
		auth = ctx.get(Authenticator)
		user = cast(User, auth.user)
		shared_board_ids = {
			share.board_id for share in store.find_by(Share, user_id=user.id)
		}
		owned_boards = store.find_by(cls, creator_id=user.id)
		shared_boards = store.query(cls).where_in(id=shared_board_ids).all()
		return [*owned_boards, *shared_boards]

	def is_accessible(self, ctx: Context) -> bool:
		auth = ctx.get(Authenticator)
		user = cast(User, auth.user)
		if self.creator_id == user.id:
			return True
		share = (
			ctx.get(Store).query(Share).where(board_id=self.id, user_id=user.id).first()
		)
		return share is not None
