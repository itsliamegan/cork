from uuid import UUID

from helios.database import Model, Store, attr
from helios.http import URL

from app.placement import Placement


class Pin(Model):
	table = "pins"

	url = attr(str)
	title = attr(str)
	note = attr(str, default="")
	creator_id = attr(UUID)

	def find_placements(self, store: Store) -> list[Placement]:
		return store.find_by(Placement, pin_id=self.id)

	def display_url(self) -> str:
		try:
			host = URL(self.url).host
		except ValueError:
			return self.url
		return host.removeprefix("www.") if host else self.url
