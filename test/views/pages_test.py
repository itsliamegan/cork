from html.parser import HTMLParser

from luna.test.assertion import assert_eq

from app import Board, Pin, Placement, Recovery, Share, User
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
		viewer = app.store.create(User, name="Viewer")
		participant = app.store.create(User, name="Participant")
		owned = app.store.create(Board, title="Reading", creator_id=viewer.id)
		shared = app.store.create(Board, title="Recipes", creator_id=participant.id)
		app.store.create(Share, board_id=owned.id, user_id=participant.id)
		app.store.create(Share, board_id=shared.id, user_id=viewer.id)
		own_pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=viewer.id,
		)
		other_pin = app.store.create(
			Pin, title="Soup", url="https://example.com/soup", creator_id=participant.id
		)
		Placement.create(app.store, own_pin, owned, viewer)
		Placement.create(app.store, other_pin, owned, participant)
		Placement.create(app.store, other_pin, shared, participant)
		Recovery.create(app.store, viewer)
		app.sign_in(viewer)
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
