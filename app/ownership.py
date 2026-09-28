from helios.database import Store

from app.board import Board
from app.pin import Pin
from app.placement import Placement
from app.user import User


class Ownership:
	def __init__(self, store: Store, user: User):
		self.store = store
		self.user = user

	def owns(self, record: Board | Pin) -> bool:
		return record.creator_id == self.user.id

	def added(self, placement: Placement) -> bool:
		return placement.adder_id == self.user.id

	def find_boards(self) -> list[Board]:
		return self.store.find_by(Board, creator_id=self.user.id)

	def find_pins(self) -> list[Pin]:
		return self.store.find_by(Pin, creator_id=self.user.id)
