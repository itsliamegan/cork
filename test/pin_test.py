from uuid import uuid4

from luna.test.assertion import assert_eq

from app import Access, Board, Pin, Placement, Share, User
from test.support import TestStore


def test_display_url_shortens_to_hostname():
	pin = Pin(
		title="Sartre",
		url="https://plato.stanford.edu/entries/sartre/",
		creator_id=uuid4(),
	)

	display_url = pin.display_url()

	assert_eq(display_url, "plato.stanford.edu")


def test_display_url_drops_www_prefix():
	pin = Pin(
		title="Example",
		url="https://www.example.com/articles",
		creator_id=uuid4(),
	)

	display_url = pin.display_url()

	assert_eq(display_url, "example.com")


def test_display_url_falls_back_to_url_without_a_host():
	pin = Pin(title="Notes", url="notes about sartre", creator_id=uuid4())

	display_url = pin.display_url()

	assert_eq(display_url, "notes about sartre")


def test_pin_without_placements_is_unfiled():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)

		placements = pin.find_placements(store)

		assert_eq(placements, [])


def test_find_placements_returns_only_this_pins_placements():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		reading = store.create(Board, title="Reading", creator_id=creator.id)
		essays = store.create(Board, title="Essays", creator_id=creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		other_pin = store.create(
			Pin,
			title="Beauvoir",
			url="https://plato.stanford.edu/entries/beauvoir/",
			creator_id=creator.id,
		)
		for board in [reading, essays]:
			Placement.create(store, pin, board, creator)
		Placement.create(store, other_pin, reading, creator)

		placements = pin.find_placements(store)

		assert_eq(
			{placement.board_id for placement in placements}, {reading.id, essays.id}
		)


def test_deleting_pin_removes_its_placements():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		reading = store.create(Board, title="Reading", creator_id=creator.id)
		essays = store.create(Board, title="Essays", creator_id=creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		for board in [reading, essays]:
			Placement.create(store, pin, board, creator)

		store.delete(pin)

		assert_eq(store.find_all(Placement), [])
		assert_eq(len(store.find_all(Board)), 2)


def test_find_accessible_placements_skips_inaccessible_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		owned = store.create(Board, title="Owned", creator_id=viewer.id)
		shared = store.create(Board, title="Shared", creator_id=other_creator.id)
		hidden = store.create(Board, title="Hidden", creator_id=other_creator.id)
		store.create(Share, board_id=shared.id, user_id=viewer.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=viewer.id,
		)
		for board in [owned, shared, hidden]:
			Placement.create(store, pin, board, other_creator)

		placements = pin.find_accessible_placements(store, Access(store, viewer))

		assert_eq(
			{placement.board_id for placement in placements}, {owned.id, shared.id}
		)
