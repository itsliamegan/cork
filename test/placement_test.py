from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Board, Pin, Placement, User
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
