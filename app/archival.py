from uuid import UUID

from helios.database import Model, Store

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
