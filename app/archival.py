from uuid import UUID

from helios.database import Model, Store

from app.board import Board
from app.placement import Placement
from app.user import User


class Archival(Model):
	table = "archivals"

	placement_id: UUID
	user_id: UUID

	@classmethod
	def archive(cls, store: Store, placement: Placement, user: User) -> Archival:
		archival = (
			store.query(cls).where(placement_id=placement.id, user_id=user.id).first()
		)
		if archival is not None:
			return archival
		return store.create(cls, placement_id=placement.id, user_id=user.id)

	@classmethod
	def unarchive(cls, store: Store, placement: Placement, user: User):
		for archival in store.find_by(cls, placement_id=placement.id, user_id=user.id):
			store.delete(archival)

	@classmethod
	def arrange(cls, store: Store, board: Board, user: User) -> list[Archival]:
		placement_ids = [
			placement.id for placement in store.find_by(Placement, board_id=board.id)
		]
		archivals = (
			store.query(Archival)
			.where(user_id=user.id)
			.where_in(placement_id=placement_ids)
			.all()
		)
		archivals.sort(key=lambda archival: archival.id)
		archivals.sort(key=lambda archival: archival.created_at, reverse=True)
		return archivals
