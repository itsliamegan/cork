from uuid import UUID

from helios.database import Model, Store
from helios.http import URL

from app.placement import Placement


class Pin(Model):
	table = "pins"

	url: str
	title: str
	note: str = ""
	creator_id: UUID

	def find_placements(self, store: Store) -> list[Placement]:
		return store.find_by(Placement, pin_id=self.id)

	def display_url(self) -> str:
		try:
			host = URL(self.url).host
		except ValueError:
			return self.url
		return host.removeprefix("www.") if host else self.url
