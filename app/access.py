from uuid import UUID

from helios.database import NotFoundError, Store

from app.board import Board
from app.ownership import Ownership
from app.pin import Pin
from app.share import Share
from app.user import User


class Access:
	def __init__(self, store: Store, user: User, ownership: Ownership):
		self.store = store
		self.user = user
		self.ownership = ownership

	def owns(self, record: Board | Pin) -> bool:
		return self.ownership.owns(record)

	def allows_board(self, board: Board) -> bool:
		return self.owns(board) or Share.exists(self.store, board, self.user)

	def allows_pin(self, pin: Pin) -> bool:
		if self.owns(pin):
			return True
		board_ids = self.find_board_ids()
		return any(
			placement.board_id in board_ids
			for placement in pin.find_placements(self.store)
		)

	def find_board(self, id: UUID) -> Board:
		board = self.store.find_one(Board, id)
		if not self.allows_board(board):
			raise NotFoundError(Board, id)
		return board

	def find_board_ids(self) -> list[UUID]:
		owned_board_ids = [board.id for board in self.ownership.find_boards()]
		shared_board_ids = Share.find_board_ids(self.store, self.user)
		return [*owned_board_ids, *shared_board_ids]

	def find_boards(self) -> list[Board]:
		shared_board_ids = Share.find_board_ids(self.store, self.user)
		shared_boards = self.store.query(Board).where_in(id=shared_board_ids).all()
		return [*self.ownership.find_boards(), *shared_boards]

	def find_pin(self, id: UUID) -> Pin:
		pin = self.store.find_one(Pin, id)
		if not self.allows_pin(pin):
			raise NotFoundError(Pin, id)
		return pin
