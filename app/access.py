from uuid import UUID

from helios.database import Model, NotFoundError, Store
from helios.http import Status
from helios.http.error import HTTPError

from app.archival import Archival
from app.board import Board
from app.ownership import Ownership
from app.pin import Pin
from app.placement import Placement
from app.share import Share
from app.user import User


class NotPermitted(HTTPError):
	status = Status.FORBIDDEN

	def __init__(self, record: Model):
		self.record = record
		super().__init__(f"{type(record).__name__} {record.id} not permitted")


class Access:
	def __init__(self, store: Store, user: User):
		self.store = store
		self.user = user
		self.ownership = Ownership(store, user)

	def owns(self, record: Board | Pin) -> bool:
		return self.ownership.owns(record)

	def added(self, placement: Placement) -> bool:
		return self.ownership.added(placement)

	def allows_board(self, board: Board) -> bool:
		return self.owns(board) or Share.exists(self.store, board, self.user)

	def allows_pin(self, pin: Pin) -> bool:
		if self.owns(pin):
			return True
		else:
			board_ids = self.find_board_ids()
			return any(
				placement.board_id in board_ids
				for placement in pin.find_placements(self.store)
			)

	def find_archival(self, id: UUID) -> Archival:
		archival = self.store.find_one(Archival, id)
		placement = self.store.find_one(Placement, archival.placement_id)
		if (
			archival.user_id != self.user.id
			or placement.board_id not in self.find_board_ids()
		):
			raise NotFoundError(Archival, id)
		return archival

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
		shared_boards = Share.find_boards(self.store, self.user)
		return [*self.ownership.find_boards(), *shared_boards]

	def find_pin(self, id: UUID) -> Pin:
		pin = self.store.find_one(Pin, id)
		if not self.allows_pin(pin):
			raise NotFoundError(Pin, id)
		return pin

	def find_placement(self, id: UUID) -> Placement:
		placement = self.store.find_one(Placement, id)
		if placement.board_id not in self.find_board_ids():
			raise NotFoundError(Placement, id)
		return placement
