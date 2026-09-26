from uuid import uuid4

from luna.test.assertion import assert_eq, assert_that

from app import Board, Pin, Placement, Share, User
from test.support import TestApplication, checked_values


def test_creates_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		app.sign_in(creator)

		res = app.client.post(
			"/boards/",
			form={"title": "Reading", "user_ids": [str(participant.id)]},
		)
		boards = app.store.find_all(Board)
		shares = app.store.find_all(Share)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{boards[0].id}")
		assert_eq(len(boards), 1)
		assert_eq(boards[0].title, "Reading")
		assert_eq(boards[0].creator_id, creator.id)
		assert_eq(
			[(share.board_id, share.user_id) for share in shares],
			[(boards[0].id, participant.id)],
		)


def test_rejects_unsharable_users():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		share = app.store.create(Share, board_id=board.id, user_id=participant.id)
		app.sign_in(creator)

		for user_ids in [[str(creator.id)], [str(uuid4())]]:
			create_res = app.client.post(
				"/boards/",
				form={"title": "Essays", "user_ids": user_ids},
			)
			update_res = app.client.post(
				f"/boards/{board.id}",
				form={"_method": "PUT", "title": "Essays", "user_ids": user_ids},
			)

			assert_eq(create_res.status_code, 400)
			assert_eq(update_res.status_code, 400)
			assert_eq([stored.id for stored in app.store.find_all(Board)], [board.id])
			assert_eq(app.store.find_one(Board, board.id).title, "Reading")
			assert_eq([stored.id for stored in app.store.find_all(Share)], [share.id])


def test_edit_form_checks_current_shares():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		app.store.create(User, name="Stranger")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.store.create(Share, board_id=board.id, user_id=participant.id)
		app.sign_in(creator)

		res = app.client.get(f"/boards/{board.id}/edit")

		assert_eq(res.status_code, 200)
		assert_that('value="Reading"' in res.text)
		assert_eq(checked_values(res.text, "user_ids"), {str(participant.id)})


def test_deletes_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.sign_in(creator)

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
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		stranger = app.store.create(User, name="Stranger")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.store.create(Share, board_id=board.id, user_id=participant.id)
		pin = app.store.create(
			Pin,
			title="Stanford Entry on Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="Read the Negation section.",
			creator_id=creator.id,
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=board.id, adder_id=creator.id
		)
		app.sign_in(participant)

		res = app.client.get(f"/boards/{board.id}")

		assert_eq(res.status_code, 200)
		assert_that("Stanford Entry on Sartre" in res.text)

		res = app.client.post(
			"/pins/",
			form={
				"title": "Stanford Entry on Beauvoir",
				"url": "https://plato.stanford.edu/entries/beauvoir/",
				"note": "",
				"board_ids": str(board.id),
			},
		)
		created = app.store.find_by(Pin, title="Stanford Entry on Beauvoir")[0]

		assert_eq(res.status_code, 302)
		assert_eq(created.note, "")
		assert_eq(created.creator_id, participant.id)
		created_placement = app.store.find_by(Placement, pin_id=created.id)[0]
		assert_eq(created_placement.board_id, board.id)

		res = app.client.post(
			f"/boards/{board.id}",
			form={"_method": "PUT", "title": "Participant's Reading"},
		)

		assert_eq(res.status_code, 404)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={"_method": "DELETE"},
		)

		assert_eq(res.status_code, 404)
		assert_eq(app.store.find_one(Pin, pin.id).title, "Stanford Entry on Sartre")

		app.sign_in(stranger)

		res = app.client.get(f"/boards/{board.id}")

		assert_eq(res.status_code, 404)


def test_update_changes_board_and_its_shares():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		former_participant = app.store.create(User, name="Former participant")
		new_participant = app.store.create(User, name="New participant")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.store.create(Share, board_id=board.id, user_id=former_participant.id)
		app.sign_in(creator)

		res = app.client.post(
			f"/boards/{board.id}",
			form={
				"_method": "PUT",
				"title": "Philosophy Reading",
				"user_ids": [str(new_participant.id)],
				"return_to": f"/boards/{board.id}",
			},
		)
		shares = app.store.find_by(Share, board_id=board.id)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(app.store.find_one(Board, board.id).title, "Philosophy Reading")
		assert_eq([share.user_id for share in shares], [new_participant.id])
