from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Model, NotFoundError, Store, attr
from helios.http import URL

from app.placement import Placement
from app.user import User


class Pin(Model):
	table = "pins"

	url = attr(str)
	title = attr(str)
	note = attr(str, default="")
	creator_id = attr(UUID)

	@classmethod
	def find_owned(cls, ctx: Context, id: UUID) -> Pin:
		auth = ctx.get(Authenticator)
		user = cast(User, auth.user)
		pin = ctx.get(Store).find_one(cls, id)
		if pin.creator_id != user.id:
			raise NotFoundError(cls, id)
		return pin

	def find_placements(self, store: Store) -> list[Placement]:
		return store.find_by(Placement, pin_id=self.id)

	def display_url(self) -> str:
		try:
			host = URL(self.url).host
		except ValueError:
			return self.url
		return host.removeprefix("www.") if host else self.url
