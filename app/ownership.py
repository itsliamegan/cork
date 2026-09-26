from uuid import UUID

from helios.database import NotFoundError, Store

from app.board import Board
from app.pin import Pin
from app.user import User


class Ownership:
	def __init__(self, store: Store, user: User):
		self.store = store
		self.user = user

	def owns(self, record: Board | Pin) -> bool:
		return record.creator_id == self.user.id

	def find_board(self, id: UUID) -> Board:
		board = self.store.find_one(Board, id)
		if not self.owns(board):
			raise NotFoundError(Board, id)
		return board

	def find_boards(self) -> list[Board]:
		return self.store.find_by(Board, creator_id=self.user.id)

	def find_pin(self, id: UUID) -> Pin:
		pin = self.store.find_one(Pin, id)
		if not self.owns(pin):
			raise NotFoundError(Pin, id)
		return pin

	def find_pins(self) -> list[Pin]:
		return (
			self.store.query(Pin)
			.where(creator_id=self.user.id)
			.order_by("created_at", "desc")
			.all()
		)
