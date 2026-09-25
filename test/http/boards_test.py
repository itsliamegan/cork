from luna.test.assertion import assert_eq, assert_that

from app import Board, Pin, Placement, Share, User
from test.support import TestApplication, checked_values


def test_creates_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		app.sign_in(creator)

		res = app.client.post("/boards/", form={"title": "Reading"})
		boards = app.store.find_all(Board)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{boards[0].id}")
		assert_eq(len(boards), 1)
		assert_eq(boards[0].title, "Reading")
		assert_eq(boards[0].creator_id, creator.id)


def test_create_with_blank_title_rerenders_form():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		app.store.create(User, name="Stranger")
		app.sign_in(creator)

		for title in ["", "   "]:
			res = app.client.post(
				"/boards/",
				form={"title": title, "user_ids": [str(participant.id)]},
			)
			form = app.client.get(res.headers["Location"])

			assert_eq(res.status_code, 302)
			assert_eq(res.headers["Location"], "/boards/new")
			assert_that("Title must be provided." in form.text)
			assert_eq(checked_values(form.text, "user_ids"), {str(participant.id)})
			assert_eq(app.store.find_all(Board), [])
			assert_eq(app.store.find_all(Share), [])


def test_update_with_blank_title_rerenders_form():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		newcomer = app.store.create(User, name="Newcomer")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.store.create(Share, board_id=board.id, user_id=participant.id)
		app.sign_in(creator)

		for title in ["", "   "]:
			res = app.client.post(
				f"/boards/{board.id}",
				form={
					"_method": "PUT",
					"title": title,
					"user_ids": [str(newcomer.id)],
					"return_to": "/boards/",
				},
			)
			form = app.client.get(res.headers["Location"])
			shares = app.store.find_by(Share, board_id=board.id)

			assert_eq(res.status_code, 302)
			assert_eq(res.headers["Location"], f"/boards/{board.id}/edit")
			assert_that("Title must be provided." in form.text)
			assert_eq(checked_values(form.text, "user_ids"), {str(newcomer.id)})
			assert_that('name="return_to" value="/boards/"' in form.text)
			assert_eq(app.store.find_one(Board, board.id).title, "Reading")
			assert_eq([share.user_id for share in shares], [participant.id])


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
				"board_id": str(board.id),
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


def test_revokes_shared_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		former_participant = app.store.create(User, name="Former participant")
		new_participant = app.store.create(User, name="New participant")
		app.sign_in(creator)

		res = app.client.post(
			"/boards/",
			form={
				"title": "Reading",
				"user_ids": [str(former_participant.id)],
			},
		)
		board = app.store.find_all(Board)[0]
		shares = app.store.find_by(Share, board_id=board.id)

		assert_eq(res.status_code, 302)
		assert_eq([share.user_id for share in shares], [former_participant.id])

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
		assert_eq(app.store.find_one(Board, board.id).title, "Philosophy Reading")
		assert_eq([share.user_id for share in shares], [new_participant.id])

		app.sign_in(former_participant)

		assert_eq(app.client.get(f"/boards/{board.id}").status_code, 404)

		app.sign_in(new_participant)

		assert_eq(app.client.get(f"/boards/{board.id}").status_code, 200)


def test_board_overflow_menu_offers_edit_and_delete_without_sharing():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.sign_in(creator)

		index_res = app.client.get("/boards/")
		edit_res = app.client.get(f"/boards/{board.id}/edit")

		assert_that(
			"pins will remain in Pins and on any other boards" in index_res.text
		)
		assert_that("Delete board" not in edit_res.text)


def test_board_pin_rows_target_unique_detail_frames():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://www.example.com/articles/sartre",
			creator_id=creator.id,
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=board.id, adder_id=creator.id
		)
		app.sign_in(creator)

		res = app.client.get(f"/boards/{board.id}")

		assert_eq(res.status_code, 200)
		assert_that(
			f'href="/pins/{pin.id}"' in res.text
			and f'data-turbo-frame="pin-{pin.id}-details"' in res.text
			and f'<turbo-frame id="pin-{pin.id}-details"' in res.text
		)
		assert_that("Also on" not in res.text and "Only on this board" not in res.text)
