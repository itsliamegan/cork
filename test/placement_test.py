from helios.database import Store
from helios.http import URL
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Access, Archival, Board, Move, Pin, Placement, Share, User
from app.access import NotPermitted
from app.move import OutOfDate
from test.support import TestStore, ids


def place_pins(store: Store, board: Board, adder: User, count: int) -> list[Placement]:
	placements = []
	for index in range(count):
		pin = store.create(
			Pin,
			title=f"Pin {index}",
			url=URL.parse(f"https://example.com/{index}"),
			creator_id=adder.id,
		)
		placements.append(Placement.create(store, pin, board, adder))
	return placements


def test_placement_is_unique_for_each_pin_and_board_pair():
	with TestStore() as store:
		adder = store.create(User, name="Adder")
		reading = store.create(Board, title="Reading", creator_id=adder.id)
		essays = store.create(Board, title="Essays", creator_id=adder.id)
		first_pin = store.create(
			Pin,
			title="First pin",
			url=URL.parse("https://first.example"),
			creator_id=adder.id,
		)
		second_pin = store.create(
			Pin,
			title="Second pin",
			url=URL.parse("https://second.example"),
			creator_id=adder.id,
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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=board_creator.id,
		)

		placement = Placement.create(store, pin, board, adder)

		assert_eq(placement.adder_id, adder.id)
		assert_eq(placement.position, 0)


def test_find_adder_without_placements_is_none():
	adder = Placement.find_adder([])

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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=board_creator.id,
		)
		placements = [
			Placement.create(store, pin, reading, board_creator),
			Placement.create(store, pin, essays, participant),
		]
		store.load(placements, "adder")

		reading_adder = Placement.find_adder(placements, reading.id)
		essays_adder = Placement.find_adder(placements, essays.id)

		assert reading_adder is not None
		assert essays_adder is not None
		assert_eq(reading_adder.id, board_creator.id)
		assert_eq(essays_adder.id, participant.id)


def test_find_adder_without_a_board_is_stable_across_orderings():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		participant = store.create(User, name="Participant")
		reading = store.create(Board, title="Reading", creator_id=board_creator.id)
		essays = store.create(Board, title="Essays", creator_id=board_creator.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=board_creator.id,
		)
		placements = [
			Placement.create(store, pin, reading, board_creator),
			Placement.create(store, pin, essays, participant),
		]
		store.load(placements, "adder")

		forward = Placement.find_adder(placements)
		backward = Placement.find_adder(list(reversed(placements)))

		assert forward is not None
		assert backward is not None
		assert_eq(forward.id, backward.id)


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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=viewer.id,
		)
		retained = Placement.create(store, pin, reading, other_creator)
		Placement.create(store, pin, essays, viewer)
		access = Access(store, viewer)

		Placement.replace(store, pin, [reading, unread], access)

		store.load(pin, "placements")
		placements = {placement.board_id: placement for placement in pin.placements}
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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=viewer.id,
		)
		Placement.create(store, pin, visible, viewer)
		hidden_placement = Placement.create(store, pin, hidden, hidden_creator)

		Placement.replace(store, pin, [], Access(store, viewer))

		store.load(pin, "placements")
		placements = pin.placements
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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=viewer.id,
		)

		Placement.replace(
			store,
			pin,
			[reading, essays, reading],
			Access(store, viewer),
		)

		store.load(pin, "placements")
		placements = pin.placements
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
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=viewer.id,
		)
		placement = Placement.create(store, pin, reading, viewer)

		with assert_raises(ValueError):
			Placement.replace(store, pin, [private], Access(store, viewer))

		store.load(pin, "placements")
		placements = pin.placements
		assert_eq([stored.id for stored in placements], [placement.id])


def test_arrange_sorts_by_position_first():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		first, second, third = place_pins(store, reading, viewer, 3)
		for position, placement in enumerate([second, third, first]):
			store.update(placement, position=position)

		placements = Placement.arrange(store, reading)

		assert_eq(ids(placements), ids([second, third, first]))


def test_arrange_sorts_equal_positions_newest_first():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		first, second, third = place_pins(store, reading, viewer, 3)

		placements = Placement.arrange(store, reading)

		assert_eq(ids(placements), ids([third, second, first]))


def test_arrange_sorts_a_pin_added_back_to_a_board_first():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		placements = place_pins(store, reading, viewer, 3)
		for position, placement in enumerate(placements):
			store.update(placement, position=position)
		readded = store.find_one(Pin, placements[2].pin_id)
		access = Access(store, viewer)
		Placement.replace(store, readded, [], access)
		Placement.replace(store, readded, [reading], access)

		arranged = Placement.arrange(store, reading)

		assert_eq(
			[placement.pin_id for placement in arranged],
			[readded.id, placements[0].pin_id, placements[1].pin_id],
		)


def test_move_renumbers_the_whole_board():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		third, second, first = place_pins(store, reading, viewer, 3)

		Placement.move(store, reading, viewer, Move(first.id, second.id, third.id))

		placements = Placement.arrange(store, reading)
		assert_eq(ids(placements), ids([second, first, third]))
		assert_eq([placement.position for placement in placements], [0, 1, 2])


def test_move_that_changes_nothing_writes_nothing():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		placements = place_pins(store, reading, viewer, 3)
		for position, placement in zip([0, 5, 9], placements):
			store.update(placement, position=position)
		first, second, third = placements

		Placement.move(store, reading, viewer, Move(second.id, first.id, third.id))

		assert_eq(
			[
				store.find_one(Placement, placement.id).position
				for placement in placements
			],
			[0, 5, 9],
		)


def test_move_of_a_placement_on_another_board_is_out_of_date():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		essays = store.create(Board, title="Essays", creator_id=viewer.id)
		second, first = place_pins(store, reading, viewer, 2)
		(elsewhere,) = place_pins(store, essays, viewer, 1)

		with assert_raises(OutOfDate):
			Placement.move(
				store, reading, viewer, Move(elsewhere.id, first.id, second.id)
			)

		assert_eq(ids(Placement.arrange(store, reading)), ids([first, second]))
		assert_eq(
			[
				store.find_one(Placement, placement.id).position
				for placement in [first, second, elsewhere]
			],
			[0, 0, 0],
		)


def test_move_next_to_a_deleted_placement_is_out_of_date():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		third, second, first = place_pins(store, reading, viewer, 3)
		store.delete(second)

		with assert_raises(OutOfDate):
			Placement.move(store, reading, viewer, Move(third.id, first.id, second.id))

		assert_eq(
			[
				store.find_one(Placement, placement.id).position
				for placement in [first, third]
			],
			[0, 0],
		)


def test_move_renumbers_archived_placements_too():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		placements = place_pins(store, reading, viewer, 3)
		for position, placement in zip([0, 5, 9], placements):
			store.update(placement, position=position)
		first, archived, last = placements
		Archival.create(store, archived, viewer)

		Placement.move(store, reading, viewer, Move(last.id, None, first.id))

		arranged = Placement.arrange(store, reading)
		assert_eq(ids(arranged), ids([last, first, archived]))
		assert_eq([placement.position for placement in arranged], [0, 1, 2])


def test_move_ignores_another_users_archivals():
	with TestStore() as store:
		viewer = store.create(User, name="Viewer")
		other_reader = store.create(User, name="Other reader")
		reading = store.create(Board, title="Reading", creator_id=viewer.id)
		Share.replace(store, reading, [other_reader])
		third, second, first = place_pins(store, reading, viewer, 3)
		Archival.create(store, second, other_reader)

		with assert_raises(OutOfDate):
			Placement.move(store, reading, viewer, Move(third.id, first.id, None))
		with assert_raises(OutOfDate):
			Placement.move(store, reading, viewer, Move(first.id, None, third.id))

		assert_eq(ids(Placement.arrange(store, reading)), ids([first, second, third]))


def test_pin_creator_board_creator_and_adder_may_remove_a_placement():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		pin_creator = store.create(User, name="Pin creator")
		adder = store.create(User, name="Adder")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		for user in [pin_creator, adder, participant]:
			store.create(Share, board_id=board.id, user_id=user.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=pin_creator.id,
		)
		placement = Placement.create(store, pin, board, adder)
		store.load(placement, "pin", "board")

		assert_that(placement.is_removable_by(Access(store, pin_creator)))
		assert_that(placement.is_removable_by(Access(store, board_creator)))
		assert_that(placement.is_removable_by(Access(store, adder)))
		assert_that(not placement.is_removable_by(Access(store, participant)))


def test_adder_removes_a_placement():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		adder = store.create(User, name="Adder")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		store.create(Share, board_id=board.id, user_id=adder.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=board_creator.id,
		)
		placement = Placement.create(store, pin, board, adder)
		store.load(placement, "pin", "board")

		placement.remove(store, Access(store, adder))

		assert_eq(store.find_all(Placement), [])


def test_participant_may_not_remove_another_users_placement():
	with TestStore() as store:
		board_creator = store.create(User, name="Board creator")
		participant = store.create(User, name="Participant")
		board = store.create(Board, title="Reading", creator_id=board_creator.id)
		store.create(Share, board_id=board.id, user_id=participant.id)
		pin = store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://plato.stanford.edu/entries/sartre/"),
			creator_id=board_creator.id,
		)
		placement = Placement.create(store, pin, board, board_creator)
		store.load(placement, "pin", "board")

		with assert_raises(NotPermitted):
			placement.remove(store, Access(store, participant))

		assert_eq(
			[stored.id for stored in store.find_all(Placement)],
			[placement.id],
		)
