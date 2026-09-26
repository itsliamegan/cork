from helios.database import Store

from app.access import Access
from app.board import Board
from app.ownership import Ownership
from app.pin import Pin
from app.placement import Placement
from app.user import User


class Removal:
	def __init__(self, placement: Placement, pin: Pin, board: Board):
		self.placement = placement
		self.pin = pin
		self.board = board

	def is_authorized(self, store: Store, user: User) -> bool:
		return Access(Ownership(store, user)).allows_board(self.board) and user.id in {
			self.pin.creator_id,
			self.placement.adder_id,
			self.board.creator_id,
		}
