from html.parser import HTMLParser

from luna.test.assertion import assert_eq

from app.data import Board, Pin, Placement, Recovery, Share, User
from test.support import TestApplication

REFERENCE_ATTRIBUTES = {
	"aria-controls",
	"aria-describedby",
	"aria-labelledby",
	"commandfor",
	"for",
	"form",
	"list",
	"popovertarget",
}


class References(HTMLParser):
	def __init__(self):
		super().__init__()
		self.ids: set[str] = set()
		self.references: list[tuple[str, str]] = []

	def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
		for name, value in attrs:
			if value is None:
				continue
			if name == "id":
				self.ids.add(value)
			elif name in REFERENCE_ATTRIBUTES:
				for id in value.split():
					self.references.append((name, id))


def test_every_page_reference_names_an_element_on_the_page():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		owned = app.store.create(Board, title="Reading", creator_id=alice.id)
		shared = app.store.create(Board, title="Recipes", creator_id=bob.id)
		app.store.create(Share, board_id=owned.id, user_id=bob.id)
		app.store.create(Share, board_id=shared.id, user_id=alice.id)
		own_pin = app.store.create(
			Pin, title="Sartre", url="https://example.com/sartre", creator_id=alice.id
		)
		other_pin = app.store.create(
			Pin, title="Soup", url="https://example.com/soup", creator_id=bob.id
		)
		Placement.create(app.store, own_pin, owned, alice)
		Placement.create(app.store, other_pin, owned, bob)
		Placement.create(app.store, other_pin, shared, bob)
		Recovery.create(app.store, alice)
		app.sign_in(alice)
		paths = [
			"/boards/",
			"/boards/new",
			f"/boards/{owned.id}",
			f"/boards/{owned.id}/edit",
			f"/boards/{shared.id}",
			"/pins/",
			"/pins/new",
			f"/pins/{own_pin.id}",
			f"/pins/{own_pin.id}/edit",
			f"/pins/{other_pin.id}",
			"/settings",
		]

		broken = []
		for path in paths:
			res = app.client.get(path)
			assert_eq(res.status_code, 200)
			page = References()
			page.feed(res.text)
			broken.extend(
				(path, name, id) for name, id in page.references if id not in page.ids
			)

		assert_eq(broken, [])
