from uuid import UUID

from helios.database import NotFoundError

from app.board import Board
from app.ownership import Ownership
from app.pin import Pin
from app.share import Share


class Access:
	def __init__(self, ownership: Ownership):
		self.ownership = ownership
		self.store = ownership.store
		self.user = ownership.user

	def allows_board(self, board: Board) -> bool:
		if self.ownership.owns(board):
			return True
		share = (
			self.store.query(Share)
			.where(board_id=board.id, user_id=self.user.id)
			.first()
		)
		return share is not None

	def allows_pin(self, pin: Pin) -> bool:
		if self.ownership.owns(pin):
			return True
		board_ids = [
			placement.board_id for placement in pin.find_placements(self.store)
		]
		owned_board = (
			self.store.query(Board)
			.where_in(id=board_ids)
			.where(creator_id=self.user.id)
			.first()
		)
		share = (
			self.store.query(Share)
			.where_in(board_id=board_ids)
			.where(user_id=self.user.id)
			.first()
		)
		return owned_board is not None or share is not None

	def find_board(self, id: UUID) -> Board:
		board = self.store.find_one(Board, id)
		if not self.allows_board(board):
			raise NotFoundError(Board, id)
		return board

	def find_boards(self) -> list[Board]:
		shared_board_ids = {
			share.board_id for share in self.store.find_by(Share, user_id=self.user.id)
		}
		shared_boards = self.store.query(Board).where_in(id=shared_board_ids).all()
		return [*self.ownership.find_boards(), *shared_boards]

	def find_pin(self, id: UUID) -> Pin:
		pin = self.store.find_one(Pin, id)
		if not self.allows_pin(pin):
			raise NotFoundError(Pin, id)
		return pin
