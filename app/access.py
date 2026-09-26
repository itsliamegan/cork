from uuid import UUID

from helios.database import NotFoundError

from app.board import Board
from app.ownership import Ownership
from app.pin import Pin
from app.share import Share


class Access:
	# Accessible board IDs are loaded once, so an Access lasts for one request.
	def __init__(self, ownership: Ownership):
		self.ownership = ownership
		self.store = ownership.store
		self.user = ownership.user
		self.board_ids: set[UUID] | None = None

	def allows_board(self, board: Board) -> bool:
		return board.id in self.find_board_ids()

	def allows_pin(self, pin: Pin) -> bool:
		if self.ownership.owns(pin):
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

	def find_board_ids(self) -> set[UUID]:
		if self.board_ids is None:
			owned = {board.id for board in self.ownership.find_boards()}
			shared = {
				share.board_id
				for share in self.store.find_by(Share, user_id=self.user.id)
			}
			self.board_ids = owned | shared
		return self.board_ids

	def find_boards(self) -> list[Board]:
		return self.store.query(Board).where_in(id=self.find_board_ids()).all()

	def find_pin(self, id: UUID) -> Pin:
		pin = self.store.find_one(Pin, id)
		if not self.allows_pin(pin):
			raise NotFoundError(Pin, id)
		return pin
