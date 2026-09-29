from luna.test.assertion import assert_eq

from app import Access, Archival, Board, Pin, Placement, Share, User
from test.support import TestStore


def test_archiving_twice_keeps_the_first_archival():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(store, pin, board, reader)
		first = Archival.create(store, placement, reader)

		Archival.create(store, placement, reader)

		archivals = store.find_all(Archival)
		assert_eq([archival.id for archival in archivals], [first.id])
		assert_eq(archivals[0].created_at, first.created_at)


def test_archiving_and_unarchiving_keep_every_position():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		placements = []
		for index in range(3):
			pin = store.create(
				Pin,
				title=f"Pin {index}",
				url=f"https://example.com/{index}",
				creator_id=reader.id,
			)
			placement = Placement.create(store, pin, board, reader)
			store.update(placement, position=index * 5)
			placements.append(placement)

		archival = Archival.create(store, placements[1], reader)
		archived = [
			store.find_one(Placement, placement.id).position for placement in placements
		]
		store.delete(archival)
		unarchived = [
			store.find_one(Placement, placement.id).position for placement in placements
		]

		assert_eq(archived, [0, 5, 10])
		assert_eq(unarchived, [0, 5, 10])


def test_removing_a_pin_from_the_board_deletes_its_archival():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(store, pin, board, reader)
		Archival.create(store, placement, reader)

		Placement.replace(store, pin, [], Access(store, reader))

		assert_eq(store.find_all(Archival), [])


def test_deleting_the_pin_deletes_its_archival():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(store, pin, board, reader)
		Archival.create(store, placement, reader)

		store.delete(pin)

		assert_eq(store.find_all(Archival), [])


def test_deleting_the_board_deletes_its_archivals():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(store, pin, board, reader)
		Archival.create(store, placement, reader)

		store.delete(board)

		assert_eq(store.find_all(Archival), [])


def test_a_pin_added_back_to_the_board_has_no_archival():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(store, pin, board, reader)
		Archival.create(store, placement, reader)
		access = Access(store, reader)

		Placement.replace(store, pin, [], access)
		Placement.replace(store, pin, [board], access)

		assert_eq(len(pin.find_placements(store)), 1)
		assert_eq(store.find_all(Archival), [])


def test_unsharing_the_board_keeps_the_recipients_archival():
	with TestStore() as store:
		owner = store.create(User, name="Owner")
		recipient = store.create(User, name="Recipient")
		board = store.create(Board, title="Reading", creator_id=owner.id)
		Share.replace(store, board, [recipient])
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(store, pin, board, owner)
		archival = Archival.create(store, placement, recipient)

		Share.replace(store, board, [])

		assert_eq(
			[archival.id for archival in store.find_all(Archival)],
			[archival.id],
		)


def test_arrange_lists_the_newest_archival_first():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		placements = []
		for index in range(3):
			pin = store.create(
				Pin,
				title=f"Pin {index}",
				url=f"https://example.com/{index}",
				creator_id=reader.id,
			)
			placements.append(Placement.create(store, pin, board, reader))
		first = Archival.create(store, placements[2], reader)
		second = Archival.create(store, placements[0], reader)
		third = Archival.create(store, placements[1], reader)

		archivals = Archival.arrange(store, board, reader)

		assert_eq(
			[archival.id for archival in archivals],
			[third.id, second.id, first.id],
		)


def test_arrange_lists_only_the_users_archivals_on_the_board():
	with TestStore() as store:
		reader = store.create(User, name="Reader")
		other_reader = store.create(User, name="Other reader")
		board = store.create(Board, title="Reading", creator_id=reader.id)
		other_board = store.create(Board, title="Essays", creator_id=reader.id)
		Share.replace(store, board, [other_reader])
		pin = store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(store, pin, board, reader)
		elsewhere = Placement.create(store, pin, other_board, reader)
		archival = Archival.create(store, placement, reader)
		Archival.create(store, elsewhere, reader)
		Archival.create(store, placement, other_reader)

		archivals = Archival.arrange(store, board, reader)

		assert_eq([archival.id for archival in archivals], [archival.id])
