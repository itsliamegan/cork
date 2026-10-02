from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store, belongs_to, has_many

from app.placement import Placement
from app.user import User

if TYPE_CHECKING:
	from app.access import Access
	from app.board import Board


class Pin(Model):
	table = "pins"

	url: str | None = None
	title: str
	note: str = ""
	creator_id: UUID
	creator: User = belongs_to("creator_id")
	placements: list[Placement] = has_many("pin_id")

	@classmethod
	def create(
		cls,
		store: Store,
		access: Access,
		title: str,
		url: str | None,
		note: str,
		boards: list[Board],
	) -> Pin:
		pin = store.create(
			cls,
			title=title,
			url=url,
			note=note,
			creator_id=access.user.id,
		)
		Placement.replace(store, pin, boards, access)
		return pin

	def edit(
		self,
		store: Store,
		access: Access,
		title: str,
		url: str | None,
		note: str,
		boards: list[Board],
	):
		from app.access import NotPermitted

		if not self.is_editable_by(access):
			raise NotPermitted(self)

		Placement.replace(store, self, boards, access)
		store.update(self, url=url, title=title, note=note)

	def is_editable_by(self, access: Access) -> bool:
		return access.owns(self)

	def delete(self, store: Store, access: Access):
		from app.access import NotPermitted

		if not self.is_deletable_by(access):
			raise NotPermitted(self)

		store.delete(self)

	def is_deletable_by(self, access: Access) -> bool:
		return access.owns(self)

	def is_unfiled(self) -> bool:
		return not self.placements

	def find_accessible_placements(
		self,
		store: Store,
		access: Access,
	) -> list[Placement]:
		return (
			store.query(Placement)
			.where({"pin_id": self.id})
			.where_any(*access.board_conditions("board"))
			.all()
		)
