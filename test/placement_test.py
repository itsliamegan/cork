from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Board, Pin, Placement, User
from test.support import TestStore


def test_placement_is_unique_for_each_pin_and_board_pair():
	with TestStore() as store:
		user = store.create(User, name="Alice")
		reading = store.create(Board, title="Reading", creator_id=user.id)
		essays = store.create(Board, title="Essays", creator_id=user.id)
		first_pin = store.create(
			Pin, title="First pin", url="https://first.example", creator_id=user.id
		)
		second_pin = store.create(
			Pin, title="Second pin", url="https://second.example", creator_id=user.id
		)
		Placement.create(store, first_pin, reading, user)

		with assert_raises(ValueError):
			Placement.create(store, first_pin, reading, user)
		Placement.create(store, first_pin, essays, user)
		Placement.create(store, second_pin, reading, user)

		assert_eq(len(store.find_all(Placement)), 3)


def test_create_records_adder_at_default_position():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		adder = store.create(User, name="Adder")
		board = store.create(Board, title="Reading", creator_id=owner.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=owner.id
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
		owner = store.create(User, name="Owner")
		reader = store.create(User, name="Reader")
		reading = store.create(Board, title="Reading", creator_id=owner.id)
		essays = store.create(Board, title="Essays", creator_id=owner.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=owner.id
		)
		placements = [
			Placement.create(store, pin, reading, owner),
			Placement.create(store, pin, essays, reader),
		]

		reading_adder = Placement.find_adder(store, placements, reading.id)
		essays_adder = Placement.find_adder(store, placements, essays.id)

		assert_that(reading_adder is owner)
		assert_that(essays_adder is reader)


def test_find_adder_without_a_board_is_stable_across_orderings():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		reader = store.create(User, name="Reader")
		reading = store.create(Board, title="Reading", creator_id=owner.id)
		essays = store.create(Board, title="Essays", creator_id=owner.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=owner.id
		)
		placements = [
			Placement.create(store, pin, reading, owner),
			Placement.create(store, pin, essays, reader),
		]

		forward = Placement.find_adder(store, placements)
		backward = Placement.find_adder(store, list(reversed(placements)))

		assert_that(forward is not None)
		assert_that(forward is backward)
