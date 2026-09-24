from uuid import uuid4

from luna.test.assertion import assert_eq

from app import Board, Pin, Placement, User
from test.support import TestStore


def test_display_url_shortens_to_hostname():
	pin = Pin(
		title="Sartre",
		url="https://www.example.com/articles/sartre",
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
		user = store.create(User, name="Alice")
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)

		placements = pin.find_placements(store)

		assert_eq(placements, [])


def test_find_placements_returns_only_this_pins_placements():
	with TestStore() as store:
		user = store.create(User, name="Alice")
		reading = store.create(Board, title="Reading", creator_id=user.id)
		essays = store.create(Board, title="Essays", creator_id=user.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)
		other_pin = store.create(
			Pin, title="Beauvoir", url="https://example.org", creator_id=user.id
		)
		for board in [reading, essays]:
			Placement.create(store, pin, board, user)
		Placement.create(store, other_pin, reading, user)

		placements = pin.find_placements(store)

		assert_eq(
			{placement.board_id for placement in placements}, {reading.id, essays.id}
		)


def test_deleting_pin_removes_its_placements():
	with TestStore() as store:
		user = store.create(User, name="Alice")
		reading = store.create(Board, title="Reading", creator_id=user.id)
		essays = store.create(Board, title="Essays", creator_id=user.id)
		pin = store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)
		for board in [reading, essays]:
			Placement.create(store, pin, board, user)

		store.delete(pin)

		assert_eq(store.find_all(Placement), [])
		assert_eq(len(store.find_all(Board)), 2)
