from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store

from app.user import User

if TYPE_CHECKING:
	from app.access import Access


class Board(Model):
	table = "boards"

	title: str
	creator_id: UUID

	@classmethod
	def create(
		cls,
		store: Store,
		creator: User,
		title: str,
		users: list[User],
	) -> Board:
		from app.share import Share

		board = store.create(cls, title=title, creator_id=creator.id)
		Share.replace(store, board, users)
		return board

	def is_editable_by(self, access: Access) -> bool:
		return access.owns(self)

	def is_deletable_by(self, access: Access) -> bool:
		return access.owns(self)

	def edit(self, store: Store, access: Access, title: str, users: list[User]):
		from app.access import NotPermitted
		from app.share import Share

		if not self.is_editable_by(access):
			raise NotPermitted(self)
		Share.replace(store, self, users)
		self.title = title
		store.save(self)

	def delete(self, store: Store, access: Access):
		from app.access import NotPermitted

		if not self.is_deletable_by(access):
			raise NotPermitted(self)
		store.delete(self)
