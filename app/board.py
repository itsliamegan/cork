from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store, belongs_to, has_many

from app.user import User

if TYPE_CHECKING:
	from app.access import Access
	from app.share import Share


class Board(Model):
	table = "boards"

	title: str
	creator_id: UUID
	creator: User = belongs_to("creator_id")
	shares: list[Share] = has_many("board_id")

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

	def edit(self, store: Store, access: Access, title: str, users: list[User]):
		from app.access import NotPermitted
		from app.share import Share

		if not self.is_editable_by(access):
			raise NotPermitted(self)

		Share.replace(store, self, users)
		store.update(self, title=title)

	def members(self) -> list[User]:
		return [self.creator, *(share.user for share in self.shares)]

	def is_editable_by(self, access: Access) -> bool:
		return access.owns(self)

	def delete(self, store: Store, access: Access):
		from app.access import NotPermitted

		if not self.is_deletable_by(access):
			raise NotPermitted(self)

		store.delete(self)

	def is_deletable_by(self, access: Access) -> bool:
		return access.owns(self)
