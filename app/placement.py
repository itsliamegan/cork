from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store

from app.user import User

if TYPE_CHECKING:
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
