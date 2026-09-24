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
	def find_contextual(
		cls,
		placements: list[Placement],
		board_id: UUID | None = None,
	) -> Placement | None:
		if board_id is not None:
			for placement in placements:
				if placement.board_id == board_id:
					return placement
		if not placements:
			return None
		return min(placements, key=lambda placement: str(placement.id))
