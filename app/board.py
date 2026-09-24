from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Model, NotFoundError, Store, attr

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
