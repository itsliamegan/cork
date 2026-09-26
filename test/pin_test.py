from uuid import uuid4

from luna.test.assertion import assert_eq, assert_raises

from app import Access, Board, Ownership, Pin, Placement, Share, User
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


def test_find_placements_with_access_skips_inaccessible_boards():
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

		placements = pin.find_placements(store, Access(Ownership(store, viewer)))

		assert_eq(
			{placement.board_id for placement in placements}, {owned.id, shared.id}
		)


def test_place_on_adds_and_removes_placements_and_keeps_retained_ones():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_creator = store.create(User, name="Other creator")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		essays = store.create(Board, title="Essays", creator_id=viewer.id)
		unread = store.create(Board, title="Unread", creator_id=viewer.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=viewer.id,
		)
		retained = Placement.create(store, pin, reading, other_creator)
		Placement.create(store, pin, essays, viewer)
		access = Access(Ownership(store, viewer))

		pin.place_on(store, [reading, unread], access)

		placements = {
			placement.board_id: placement for placement in pin.find_placements(store)
		}
		assert_eq(set(placements), {reading.id, unread.id})
		kept = placements[reading.id]
		assert_eq(
			(kept.id, kept.created_at, kept.adder_id),
			(retained.id, retained.created_at, other_creator.id),
		)
		assert_eq(placements[unread.id].adder_id, viewer.id)


def test_place_on_keeps_placements_on_inaccessible_boards():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		hidden_creator = store.create(User, name="Hidden creator")
		visible = store.create(Board, title="Visible", creator_id=viewer.id)
		hidden = store.create(Board, title="Hidden", creator_id=hidden_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=viewer.id,
		)
		Placement.create(store, pin, visible, viewer)
		hidden_placement = Placement.create(store, pin, hidden, hidden_creator)

		pin.place_on(store, [], Access(Ownership(store, viewer)))

		placements = pin.find_placements(store)
		assert_eq([placement.id for placement in placements], [hidden_placement.id])
		assert_eq(placements[0].created_at, hidden_placement.created_at)


def test_place_on_places_a_new_pin_once_per_board():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		essays = store.create(Board, title="Essays", creator_id=viewer.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=viewer.id,
		)

		pin.place_on(
			store,
			[reading, essays, reading],
			Access(Ownership(store, viewer)),
		)

		placements = pin.find_placements(store)
		assert_eq(len(placements), 2)
		assert_eq(
			{placement.board_id for placement in placements}, {reading.id, essays.id}
		)


def test_place_on_refuses_inaccessible_boards_without_changes():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		stranger = store.create(User, name="Stranger")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		private = store.create(Board, title="Private", creator_id=stranger.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=viewer.id,
		)
		placement = Placement.create(store, pin, reading, viewer)

		with assert_raises(ValueError):
			pin.place_on(store, [private], Access(Ownership(store, viewer)))

		placements = pin.find_placements(store)
		assert_eq([stored.id for stored in placements], [placement.id])
