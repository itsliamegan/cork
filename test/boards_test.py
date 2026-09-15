from luna.test.assertion import assert_eq, assert_that

from app.data import Board, Ordering, Pin, Placement, Share, User
from test.support import TestApplication


def test_creates_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		res = app.client.post("/boards/", form={"title": "Reading"})
		boards = app.store.find_all(Board)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{boards[0].id}")
		assert_eq(len(boards), 1)
		assert_eq(boards[0].title, "Reading")
		assert_eq(boards[0].creator_id, user.id)


def test_deletes_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", creator_id=user.id)
		app.sign_in(user)

		res = app.client.post(
			f"/boards/{board.id}",
			form={"_method": "DELETE"},
		)
		boards = app.store.find_all(Board)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/boards/")
		assert_eq(boards, [])


def test_shares_board():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		charlie = app.store.create(User, name="Charlie")
		board = app.store.create(Board, title="Reading", creator_id=alice.id)
		app.store.create(Share, board_id=board.id, user_id=bob.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="Read the Negation section.",
			creator_id=alice.id,
		)
		app.store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=alice.id)
		app.sign_in(bob)

		res = app.client.get(f"/boards/{board.id}")

		assert_eq(res.status_code, 200)
		assert_that("Stanford Entry on Sartre" in res.text)

		res = app.client.post(
			"/pins/",
			form={
				"title": "Stanford Entry on Beauvoir",
				"url": "https://plato.stanford.edu/entries/beauvoir/",
				"note": "",
				"board_id": str(board.id),
			},
		)
		created = app.store.find_by(Pin, title="Stanford Entry on Beauvoir")[0]

		assert_eq(res.status_code, 302)
		assert_eq(created.note, "")
		assert_eq(created.creator_id, bob.id)
		created_placement = app.store.find_by(Placement, pin_id=created.id)[0]
		assert_eq(created_placement.board_id, board.id)

		res = app.client.post(
			f"/boards/{board.id}",
			form={"_method": "PUT", "title": "Bob's Reading"},
		)

		assert_eq(res.status_code, 404)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={"_method": "DELETE"},
		)

		assert_eq(res.status_code, 404)
		assert_eq(app.store.find_one(Pin, pin.id).title, "Stanford Entry on Sartre")

		app.sign_in(charlie)

		res = app.client.get(f"/boards/{board.id}")

		assert_eq(res.status_code, 404)


def test_revokes_shared_board():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		charlie = app.store.create(User, name="Charlie")
		app.sign_in(alice)

		res = app.client.post(
			"/boards/",
			form={
				"title": "Reading",
				"user_id": [str(bob.id)],
			},
		)
		board = app.store.find_all(Board)[0]
		shares = app.store.find_by(Share, board_id=board.id)

		assert_eq(res.status_code, 302)
		assert_eq([share.user_id for share in shares], [bob.id])

		res = app.client.post(
			f"/boards/{board.id}",
			form={
				"_method": "PUT",
				"title": "Philosophy Reading",
				"user_id": [str(charlie.id)],
				"return_to": f"/boards/{board.id}",
			},
		)
		shares = app.store.find_by(Share, board_id=board.id)

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_one(Board, board.id).title, "Philosophy Reading")
		assert_eq([share.user_id for share in shares], [charlie.id])

		app.sign_in(bob)

		assert_eq(app.client.get(f"/boards/{board.id}").status_code, 404)

		app.sign_in(charlie)

		assert_eq(app.client.get(f"/boards/{board.id}").status_code, 200)


def test_deleting_board_retains_pins_placed_on_another_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=user.id,
		)
		reading_placement = app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=user.id
		)
		essays_placement = app.store.create(
			Placement, pin_id=pin.id, board_id=essays.id, adder_id=user.id
		)
		app.sign_in(user)

		res = app.client.post(f"/boards/{reading.id}", form={"_method": "DELETE"})

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_one(Pin, pin.id).id, pin.id)
		assert_eq(
			[placement.id for placement in app.store.find_all(Placement)],
			[essays_placement.id],
		)
		assert_eq([board.id for board in app.store.find_all(Board)], [essays.id])
		assert_eq(
			reading_placement.id
			in {placement.id for placement in app.store.find_all(Placement)},
			False,
		)


def test_deleted_board_cascades():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		board = app.store.create(Board, title="Reading", creator_id=alice.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=alice.id,
		)
		app.store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=alice.id)
		app.store.create(Share, board_id=board.id, user_id=bob.id)
		app.store.create(
			Ordering,
			user_id=alice.id,
			board_id=board.id,
			position=0,
		)
		app.sign_in(alice)

		res = app.client.post(
			f"/boards/{board.id}",
			form={"_method": "DELETE"},
		)

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_all(Board), [])
		assert_eq(app.store.find_all(Pin), [])
		assert_eq(app.store.find_all(Placement), [])
		assert_eq(app.store.find_all(Share), [])
		assert_eq(app.store.find_all(Ordering), [])
