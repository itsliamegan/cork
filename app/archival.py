from uuid import UUID

from helios.database import Model, Store, belongs_to

from app.board import Board
from app.placement import Placement
from app.user import User


class Archival(Model):
	table = "archivals"

	placement_id: UUID
	placement: Placement = belongs_to("placement_id")
	user_id: UUID

	@classmethod
	def create(cls, store: Store, placement: Placement, user: User) -> Archival:
		existing = (
			store.query(cls)
			.where({"placement_id": placement.id, "user_id": user.id})
			.first()
		)
		if existing is not None:
			return existing
		else:
			return store.create(cls, placement_id=placement.id, user_id=user.id)

	@classmethod
	def arrange(cls, store: Store, board: Board, user: User) -> list[Archival]:
		return (
			store.query(Archival)
			.where({"user_id": user.id, "placement.board_id": board.id})
			.order_by("created_at", "desc")
			.order_by("id")
			.all()
		)
