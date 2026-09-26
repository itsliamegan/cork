from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Access, Board, Pin, Placement, User
from test.support import TestStore


def test_placement_is_unique_for_each_pin_and_board_pair():
	with TestStore() as store:
		adder = store.create(User, name="Adder")
		reading = store.create(Board, title="Reading", creator_id=adder.id)
		essays = store.create(Board, title="Essays", creator_id=adder.id)
		first_pin = store.create(
			Pin, title="First pin", url="https://first.example", creator_id=adder.id
		)
		second_pin = store.create(
			Pin, title="Second pin", url="https://second.example", creator_id=adder.id
		)
		Placement.create(store, first_pin, reading, adder)

		with assert_raises(ValueError):
			Placement.create(store, first_pin, reading, adder)
		Placement.create(store, first_pin, essays, adder)
		Placement.create(store, second_pin, reading, adder)

		assert_eq(len(store.find_all(Placement)), 3)


def test_create_records_adder_at_default_position():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		adder = store.create(User, name="Adder")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=board_creator.id,
		)

		placement = Placement.create(store, pin, board, adder)

		assert_eq(placement.adder_id, adder.id)
		assert_eq(placement.position, 0)


def test_find_adder_without_placements_is_none():
	with TestStore() as store:
		adder = Placement.find_adder(store, [])

		assert_that(adder is None)


def test_find_adder_prefers_the_given_board():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		participant = store.create(User, name="Participant")
		reading = store.create(Board, title="Reading", creator_id=board_creator.id)
		essays = store.create(Board, title="Essays", creator_id=board_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=board_creator.id,
		)
		placements = [
			Placement.create(store, pin, reading, board_creator),
			Placement.create(store, pin, essays, participant),
		]

		reading_adder = Placement.find_adder(store, placements, reading.id)
		essays_adder = Placement.find_adder(store, placements, essays.id)

		assert_that(reading_adder is board_creator)
		assert_that(essays_adder is participant)


def test_find_adder_without_a_board_is_stable_across_orderings():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		participant = store.create(User, name="Participant")
		reading = store.create(Board, title="Reading", creator_id=board_creator.id)
		essays = store.create(Board, title="Essays", creator_id=board_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=board_creator.id,
		)
		placements = [
			Placement.create(store, pin, reading, board_creator),
			Placement.create(store, pin, essays, participant),
		]

		forward = Placement.find_adder(store, placements)
		backward = Placement.find_adder(store, list(reversed(placements)))

		assert_that(forward is not None)
		assert_that(forward is backward)


def test_replace_adds_and_removes_placements_and_keeps_retained_ones():
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
		access = Access(store, viewer)

		Placement.replace(store, pin, [reading, unread], access)

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


def test_replace_keeps_placements_on_inaccessible_boards():
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

		Placement.replace(store, pin, [], Access(store, viewer))

		placements = pin.find_placements(store)
		assert_eq([placement.id for placement in placements], [hidden_placement.id])
		assert_eq(placements[0].created_at, hidden_placement.created_at)


def test_replace_places_a_new_pin_once_per_board():
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

		Placement.replace(
			store,
			pin,
			[reading, essays, reading],
			Access(store, viewer),
		)

		placements = pin.find_placements(store)
		assert_eq(len(placements), 2)
		assert_eq(
			{placement.board_id for placement in placements}, {reading.id, essays.id}
		)


def test_replace_refuses_inaccessible_boards_without_changes():
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
			Placement.replace(store, pin, [private], Access(store, viewer))

		placements = pin.find_placements(store)
		assert_eq([stored.id for stored in placements], [placement.id])


def test_reorder_positions_placements_as_given():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		placements = []
		for index in range(3):
			pin = store.create(
				Pin,
				title=f"Pin {index}",
				url=f"https://example.com/{index}",
				creator_id=viewer.id,
			)
			placements.append(Placement.create(store, pin, reading, viewer))
		first, second, third = placements

		Placement.reorder(store, reading, [third, first, second])

		assert_eq(
			[
				store.find_one(Placement, placement.id).position
				for placement in placements
			],
			[1, 2, 0],
		)


def test_reorder_refuses_duplicate_placements_without_changes():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=viewer.id
		)
		placement = Placement.create(store, pin, reading, viewer)

		with assert_raises(ValueError):
			Placement.reorder(store, reading, [placement, placement])

		assert_eq(store.find_one(Placement, placement.id).position, 0)


def test_reorder_refuses_placements_on_other_boards_without_changes():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		essays = store.create(Board, title="Essays", creator_id=viewer.id)
		first_pin = store.create(
			Pin, title="First pin", url="https://first.example", creator_id=viewer.id
		)
		second_pin = store.create(
			Pin, title="Second pin", url="https://second.example", creator_id=viewer.id
		)
		on_reading = Placement.create(store, first_pin, reading, viewer)
		on_essays = Placement.create(store, second_pin, essays, viewer)

		with assert_raises(ValueError):
			Placement.reorder(store, reading, [on_essays, on_reading])

		assert_eq(
			[
				store.find_one(Placement, placement.id).position
				for placement in [on_reading, on_essays]
			],
			[0, 0],
		)
