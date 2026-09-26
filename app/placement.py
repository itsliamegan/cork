from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store

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
