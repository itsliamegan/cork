from typing import cast

from helios.app import Context
from helios.auth import Authenticator

from app.board import Board
from app.pin import Pin
from app.placement import Placement
from app.user import User


class Removal:
	def __init__(self, placement: Placement, pin: Pin, board: Board):
		self.placement = placement
		self.pin = pin
		self.board = board

	def is_authorized(self, ctx: Context) -> bool:
		auth = ctx.get(Authenticator)
		user = cast(User, auth.user)

		return self.board.is_accessible(ctx) and user.id in {
			self.pin.creator_id,
			self.placement.adder_id,
			self.board.creator_id,
		}
