from uuid import UUID

from helios.database import Model, NotFoundError, Store
from helios.http import Status
from helios.http.error import HTTPError

from app.archival import Archival
from app.board import Board
from app.ownership import Ownership
from app.pin import Pin
from app.placement import Placement
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

	def board_conditions(self, path: str = "") -> list[dict[str, UUID]]:
		prefix = f"{path}." if path else ""
		return [
			{f"{prefix}creator_id": self.user.id},
			{f"{prefix}shares.user_id": self.user.id},
		]

	def find_archival(self, id: UUID) -> Archival:
		archival = (
			self.store.query(Archival)
			.where({"id": id, "user_id": self.user.id})
			.where_any(*self.board_conditions("placement.board"))
			.first()
		)
		if archival is None:
			raise NotFoundError(Archival, id)
		return archival

	def find_board(self, id: UUID) -> Board:
		board = (
			self.store.query(Board)
			.where({"id": id})
			.where_any(*self.board_conditions())
			.first()
		)
		if board is None:
			raise NotFoundError(Board, id)
		return board

	def find_board_ids(self) -> list[UUID]:
		return [board.id for board in self.find_boards()]

	def find_boards(self) -> list[Board]:
		shared_boards = (
			self.store.query(Board).where({"shares.user_id": self.user.id}).all()
		)
		return [*self.ownership.find_boards(), *shared_boards]

	def find_pin(self, id: UUID) -> Pin:
		pin = (
			self.store.query(Pin)
			.where({"id": id})
			.where_any(
				{"creator_id": self.user.id},
				*self.board_conditions("placements.board"),
			)
			.first()
		)
		if pin is None:
			raise NotFoundError(Pin, id)
		return pin

	def find_placement(self, id: UUID) -> Placement:
		placement = (
			self.store.query(Placement)
			.where({"id": id})
			.where_any(*self.board_conditions("board"))
			.first()
		)
		if placement is None:
			raise NotFoundError(Placement, id)
		return placement
