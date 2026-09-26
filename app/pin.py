from typing import TYPE_CHECKING
from uuid import UUID

from helios.database import Model, Store
from helios.http import URL

from app.placement import Placement

if TYPE_CHECKING:
	from app.access import Access


class Pin(Model):
	table = "pins"

	url: str
	title: str
	note: str = ""
	creator_id: UUID

	def find_placements(self, store: Store) -> list[Placement]:
		return store.find_by(Placement, pin_id=self.id)

	def find_accessible_placements(
		self,
		store: Store,
		access: Access,
	) -> list[Placement]:
		board_ids = access.find_board_ids()
		return [
			placement
			for placement in self.find_placements(store)
			if placement.board_id in board_ids
		]

	def display_url(self) -> str:
		try:
			host = URL(self.url).host
		except ValueError:
			return self.url
		return host.removeprefix("www.") if host else self.url
