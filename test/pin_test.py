from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Access, Board, Pin, Placement, Share, User
from app.access import NotPermitted
from test.support import TestStore


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


def test_only_the_creator_may_edit_or_delete_a_pin():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		Placement.create(store, pin, board, creator)

		assert_that(pin.is_editable_by(Access(store, creator)))
		assert_that(pin.is_deletable_by(Access(store, creator)))
		assert_that(not pin.is_editable_by(Access(store, participant)))
		assert_that(not pin.is_deletable_by(Access(store, participant)))


def test_creator_edits_a_pin_and_its_placements():
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
		Placement.create(store, pin, reading, creator)

		pin.edit(
			store,
			Access(store, creator),
			title="Beauvoir",
			url="https://plato.stanford.edu/entries/beauvoir/",
			note="Read next",
			boards=[essays],
		)
		edited = store.find_one(Pin, pin.id)
		store.load(edited, "placements")

		assert_eq(edited.title, "Beauvoir")
		assert_eq(edited.url, "https://plato.stanford.edu/entries/beauvoir/")
		assert_eq(edited.note, "Read next")
		assert_eq(
			[placement.board_id for placement in edited.placements],
			[essays.id],
		)


def test_participant_may_not_edit_a_pin():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		Placement.create(store, pin, board, creator)

		with assert_raises(NotPermitted):
			pin.edit(
				store,
				Access(store, participant),
				title="Beauvoir",
				url="https://plato.stanford.edu/entries/beauvoir/",
				note="Read next",
				boards=[],
			)
		stored = store.find_one(Pin, pin.id)
		store.load(stored, "placements")

		assert_eq(stored.title, "Sartre")
		assert_eq(stored.url, "https://plato.stanford.edu/entries/sartre/")
		assert_eq(stored.note, "")
		assert_eq(
			[placement.board_id for placement in stored.placements],
			[board.id],
		)


def test_participant_may_not_delete_a_pin():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		Placement.create(store, pin, board, creator)

		with assert_raises(NotPermitted):
			pin.delete(store, Access(store, participant))

		assert_eq([stored.id for stored in store.find_all(Pin)], [pin.id])


def test_create_places_a_new_pin_on_each_chosen_board():
	with TestStore() as store:
		creator = store.create(User, name="Creator")
		reading = store.create(Board, title="Reading", creator_id=creator.id)
		essays = store.create(Board, title="Essays", creator_id=creator.id)

		pin = Pin.create(
			store,
			Access(store, creator),
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="",
			boards=[reading, essays],
		)
		store.load(pin, "placements")

		assert_eq(pin.creator_id, creator.id)
		assert_eq(
			{placement.board_id for placement in pin.placements},
			{reading.id, essays.id},
		)
