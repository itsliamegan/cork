from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store

from app.move import Move
from app.user import User

if TYPE_CHECKING:
	from app.access import Access
	from app.board import Board
	from app.pin import Pin


class Placement(Model):
	table = "placements"

	pin_id: UUID
	board_id: UUID
	adder_id: UUID
	position: int = 0

	@classmethod
	def create(
		cls,
		store: Store,
		pin: Pin,
		board: Board,
		adder: User,
	) -> Placement:
		duplicate = store.query(cls).where(pin_id=pin.id, board_id=board.id).first()
		if duplicate is not None:
			raise ValueError(f"Pin {pin.id} is already placed on Board {board.id}")
		return store.create(
			cls,
			pin_id=pin.id,
			board_id=board.id,
			adder_id=adder.id,
		)

	@classmethod
	def replace(
		cls,
		store: Store,
		pin: Pin,
		boards: list[Board],
		access: Access,
	) -> None:
		chosen_board_ids = {board.id for board in boards}
		inaccessible_board_ids = chosen_board_ids - set(access.find_board_ids())
		if inaccessible_board_ids:
			raise ValueError(f"Boards {inaccessible_board_ids} are not accessible")

		for placement in pin.find_accessible_placements(store, access):
			if placement.board_id not in chosen_board_ids:
				store.delete(placement)
		placed_board_ids = {
			placement.board_id for placement in pin.find_placements(store)
		}
		for board in boards:
			if board.id not in placed_board_ids:
				cls.create(store, pin, board, access.user)
				placed_board_ids.add(board.id)

	@classmethod
	def arrange(cls, store: Store, board: Board) -> list[Placement]:
		placements = store.find_by(Placement, board_id=board.id)
		placements.sort(key=lambda placement: placement.id)
		placements.sort(key=lambda placement: placement.created_at, reverse=True)
		placements.sort(key=lambda placement: placement.position)
		return placements

	@classmethod
	def move(cls, store: Store, board: Board, user: User, move: Move):
		from app.archival import Archival

		placements = cls.arrange(store, board)
		hidden_ids = {
			archival.placement_id for archival in Archival.arrange(store, board, user)
		}
		order = move.apply([placement.id for placement in placements], hidden_ids)
		if order is None:
			return

		placements_by_id = {placement.id: placement for placement in placements}
		for position, id in enumerate(order):
			placement = placements_by_id[id]
			placement.position = position
			store.save(placement)

	def remove(self, store: Store, access: Access, pin: Pin, board: Board):
		from app.access import NotPermitted

		if not self.is_removable_by(access, pin, board):
			raise NotPermitted(self)

		store.delete(self)

	def is_removable_by(self, access: Access, pin: Pin, board: Board) -> bool:
		return access.owns(pin) or access.owns(board) or access.added(self)

	@classmethod
	def find_adder(
		cls,
		store: Store,
		placements: list[Placement],
		board_id: UUID | None = None,
	) -> User | None:
		if not placements:
			return None
		placement = next(
			(placement for placement in placements if placement.board_id == board_id),
			min(placements, key=lambda placement: str(placement.id)),
		)
		return store.find_one(User, placement.adder_id)
