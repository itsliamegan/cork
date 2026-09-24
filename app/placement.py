from uuid import UUID

from helios.database import Model, Store, attr

from app.board import Board
from app.pin import Pin
from app.user import User


class Placement(Model):
	table = "placements"

	pin_id = attr(UUID)
	board_id = attr(UUID)
	adder_id = attr(UUID)
	position = attr(int, default=0)

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
