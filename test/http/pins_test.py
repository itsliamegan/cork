from uuid import uuid4

from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app import Board, Pin, Placement, Share, User
from test.support import TestApplication, checked_values


def test_creates_pin_with_placements_for_selected_boards():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		essays = app.store.create(Board, title="Essays", creator_id=creator.id)
		app.sign_in(creator)

		res = app.client.post(
			"/pins/",
			form={
				"title": "Stanford Entry on Sartre",
				"url": "https://plato.stanford.edu/entries/sartre/",
				"note": "Read the Negation section.",
				"board_ids": [str(essays.id), str(reading.id)],
				"return_to": f"/boards/{reading.id}",
			},
		)
		pin = app.store.find_all(Pin)[0]
		placements = app.store.find_by(Placement, pin_id=pin.id)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{reading.id}")
		assert_eq(len(placements), 2)
		assert_eq(
			{placement.board_id for placement in placements}, {reading.id, essays.id}
		)
		assert_eq({placement.adder_id for placement in placements}, {creator.id})


def test_create_rejects_repeated_board_ids():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.sign_in(creator)

		res = app.client.post(
			"/pins/",
			form={
				"title": "Sartre",
				"url": "https://plato.stanford.edu/entries/sartre/",
				"board_ids": [str(reading.id), str(reading.id)],
			},
		)

		assert_eq(res.status_code, 400)
		assert_eq(app.store.find_all(Pin), [])


def test_create_with_missing_fields_rerenders_form():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		essays = app.store.create(Board, title="Essays", creator_id=creator.id)
		app.sign_in(creator)

		res = app.client.post(
			"/pins/",
			form={
				"title": "",
				"url": "",
				"note": "Read the Negation section.",
				"board_ids": [str(essays.id)],
				"return_to": "/pins/",
			},
		)
		form = app.client.get(res.headers["Location"])

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/pins/new")
		assert_that("Title must be provided." in form.text)
		assert_that("URL must be provided." in form.text)
		assert_that(">Read the Negation section.</textarea>" in form.text)
		assert_eq(checked_values(form.text, "board_ids"), {str(essays.id)})
		assert_that('name="return_to" value="/pins/"' in form.text)
		assert_that(str(reading.id) not in checked_values(form.text, "board_ids"))
		assert_eq(app.store.find_all(Pin), [])
		assert_eq(app.store.find_all(Placement), [])


def test_create_from_board_with_missing_fields_returns_to_board_form():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.sign_in(creator)

		res = app.client.post(
			"/pins/",
			form={
				"title": "",
				"url": "https://plato.stanford.edu/entries/sartre/",
				"board_ids": [],
				"return_to": f"/boards/{reading.id}",
			},
		)
		form = app.client.get(res.headers["Location"])

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/pins/new?board_id={reading.id}")
		assert_that("Title must be provided." in form.text)
		assert_that('value="https://plato.stanford.edu/entries/sartre/"' in form.text)
		assert_eq(checked_values(form.text, "board_ids"), set())
		assert_that(f'name="return_to" value="/boards/{reading.id}"' in form.text)
		assert_eq(app.store.find_all(Pin), [])


def test_update_with_missing_fields_rerenders_form():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		essays = app.store.create(Board, title="Essays", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="Original note",
			creator_id=creator.id,
		)
		placement = app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=creator.id
		)
		app.sign_in(creator)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={
				"_method": "PUT",
				"title": "",
				"url": "",
				"note": "Changed note",
				"board_ids": [str(essays.id)],
				"return_to": "/pins/",
			},
		)
		form = app.client.get(res.headers["Location"])
		stored = app.store.find_one(Pin, pin.id)
		placements = app.store.find_by(Placement, pin_id=pin.id)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/pins/{pin.id}/edit")
		assert_that("Title must be provided." in form.text)
		assert_that("URL must be provided." in form.text)
		assert_that(">Changed note</textarea>" in form.text)
		assert_eq(checked_values(form.text, "board_ids"), {str(essays.id)})
		assert_that('name="return_to" value="/pins/"' in form.text)
		assert_eq(
			(stored.title, stored.url, stored.note),
			(
				"Sartre",
				"https://plato.stanford.edu/entries/sartre/",
				"Original note",
			),
		)
		assert_eq([placement.id for placement in placements], [placement.id])


def test_edit_form_checks_accessible_placements():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.store.create(Board, title="Essays", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="Original note",
			creator_id=creator.id,
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=creator.id
		)
		app.sign_in(creator)

		res = app.client.get(f"/pins/{pin.id}/edit")

		assert_eq(res.status_code, 200)
		assert_that('value="Sartre"' in res.text)
		assert_that(">Original note</textarea>" in res.text)
		assert_eq(checked_values(res.text, "board_ids"), {str(reading.id)})


def test_new_form_from_board_lists_every_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		essays = app.store.create(Board, title="Essays", creator_id=creator.id)
		app.sign_in(creator)

		res = app.client.get(f"/pins/new?board_id={reading.id}")

		assert_eq(res.status_code, 200)
		assert_that(reading.title in res.text)
		assert_that(essays.title in res.text)


def test_new_form_rejects_inaccessible_boards():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		stranger = app.store.create(User, name="Stranger")
		hidden = app.store.create(Board, title="Hidden", creator_id=stranger.id)
		app.sign_in(viewer)

		hidden_res = app.client.get(f"/pins/new?board_id={hidden.id}")
		malformed_res = app.client.get("/pins/new?board_id=not-a-board")

		assert_eq(hidden_res.status_code, 404)
		assert_eq(malformed_res.status_code, 404)


def test_edit_form_lists_every_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		essays = app.store.create(Board, title="Essays", creator_id=creator.id)
		unread = app.store.create(Board, title="Unread", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		for board in [reading, essays]:
			app.store.create(
				Placement, pin_id=pin.id, board_id=board.id, adder_id=creator.id
			)
		app.sign_in(creator)

		res = app.client.get(f"/pins/{pin.id}/edit")

		assert_eq(res.status_code, 200)
		for board in [reading, essays, unread]:
			assert_that(board.title in res.text)


def test_board_picker_includes_only_accessible_boards():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		first_participant = app.store.create(User, name="First participant")
		second_participant = app.store.create(User, name="Second participant")
		incoming_creator = app.store.create(User, name="Incoming creator")
		incoming_participant = app.store.create(User, name="Incoming participant")
		hidden_creator = app.store.create(User, name="Hidden creator")
		private = app.store.create(Board, title="Private notes", creator_id=viewer.id)
		shared = app.store.create(Board, title="Shared reading", creator_id=viewer.id)
		incoming = app.store.create(
			Board, title="Incoming", creator_id=incoming_creator.id
		)
		hidden = app.store.create(Board, title="Hidden", creator_id=hidden_creator.id)
		for board, user in [
			(shared, first_participant),
			(shared, second_participant),
			(incoming, viewer),
			(incoming, incoming_participant),
			(hidden, incoming_participant),
		]:
			app.store.create(Share, board_id=board.id, user_id=user.id)
		app.sign_in(viewer)

		res = app.client.get(f"/pins/new?board_id={private.id}")

		assert_eq(res.status_code, 200)
		for board in [private, shared, incoming]:
			assert_that(board.title in res.text)
		assert_that(hidden.title not in res.text)


def test_update_adds_and_removes_placements_without_replacing_retained_placements():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		essays = app.store.create(Board, title="Essays", creator_id=creator.id)
		unread = app.store.create(Board, title="Unread", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		retained = app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=creator.id
		)
		removed = app.store.create(
			Placement, pin_id=pin.id, board_id=essays.id, adder_id=creator.id
		)
		app.sign_in(creator)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={
				"_method": "PUT",
				"title": "Updated Sartre",
				"url": "https://example.com/updated",
				"note": "Updated note",
				"board_ids": [str(reading.id), str(unread.id)],
			},
		)
		placements = app.store.find_by(Placement, pin_id=pin.id)

		assert_eq(res.status_code, 302)
		assert_eq(app.store.find_one(Placement, retained.id).id, retained.id)
		with assert_raises(NotFoundError):
			app.store.find_one(Placement, removed.id)
		assert_eq(
			{placement.board_id for placement in placements}, {reading.id, unread.id}
		)
		assert_eq(app.store.find_one(Pin, pin.id).note, "Updated note")
		assert_eq(
			app.store.find_one(Placement, retained.id).created_at, retained.created_at
		)
		assert_eq(
			app.store.find_one(Placement, retained.id).adder_id, retained.adder_id
		)


def test_invalid_board_selections_do_not_partially_mutate_pins():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		stranger = app.store.create(User, name="Stranger")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		private = app.store.create(Board, title="Private", creator_id=stranger.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		placement = app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=creator.id
		)
		app.sign_in(creator)

		for board_ids in [[str(uuid4())], [str(private.id)]]:
			res = app.client.post(
				"/pins/",
				form={
					"title": "New pin",
					"url": "https://new.example",
					"board_ids": board_ids,
				},
			)
			assert_eq(res.status_code, 400)
			assert_eq(
				[stored_pin.id for stored_pin in app.store.find_all(Pin)], [pin.id]
			)

			res = app.client.post(
				f"/pins/{pin.id}",
				form={
					"_method": "PUT",
					"title": "Changed",
					"url": "https://changed.example",
					"board_ids": board_ids,
				},
			)
			assert_eq(res.status_code, 400)
			assert_eq(app.store.find_one(Pin, pin.id).title, "Sartre")
			assert_eq(app.store.find_one(Placement, placement.id).board_id, reading.id)


def test_unrelated_user_cannot_open_pin_details():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		stranger = app.store.create(User, name="Stranger")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=board.id, adder_id=creator.id
		)
		app.sign_in(stranger)

		assert_eq(app.client.get(f"/pins/{pin.id}").status_code, 404)


def test_pin_details_embed_frame_with_accessible_boards_and_actions():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		shared = app.store.create(Board, title="Shared", creator_id=creator.id)
		app.store.create(Share, board_id=shared.id, user_id=participant.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			note="Read this closely.",
			creator_id=creator.id,
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=creator.id
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=shared.id, adder_id=participant.id
		)
		app.sign_in(participant)

		res = app.client.get(f"/pins/{pin.id}")

		assert_that("https://plato.stanford.edu/entries/sartre/" in res.text)


def test_pin_details_use_referring_board_placement():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		reading = app.store.create(Board, title="Reading", creator_id=creator.id)
		essays = app.store.create(Board, title="Essays", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=creator.id
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=essays.id, adder_id=participant.id
		)
		app.sign_in(creator)

		res = app.client.get(
			f"/pins/{pin.id}", headers={"Referer": f"/boards/{essays.id}"}
		)

		assert_eq(res.status_code, 200)
		assert_that("Participant" in res.text)


def test_owned_pins_index_includes_unfiled_pins_and_hides_other_creators():
	with TestApplication() as app:
		viewer = app.store.create(User, name="Viewer")
		other_creator = app.store.create(User, name="Other creator")
		shared = app.store.create(
			Board, title="Shared reading", creator_id=other_creator.id
		)
		app.store.create(Share, board_id=shared.id, user_id=viewer.id)
		owned = app.store.create(
			Pin,
			title="Owned unfiled",
			url="https://owned.example",
			creator_id=viewer.id,
		)
		visible = app.store.create(
			Pin,
			title="Someone else's pin",
			url="https://other.example",
			creator_id=other_creator.id,
		)
		app.store.create(
			Placement, pin_id=visible.id, board_id=shared.id, adder_id=other_creator.id
		)
		app.sign_in(viewer)

		res = app.client.get("/pins/")

		assert_eq(res.status_code, 200)
		assert_that(owned.title in res.text)
		assert_that("No boards" in res.text)
		assert_that(visible.title not in res.text)


def test_pins_index_lists_every_pin_with_its_board_count():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		board = app.store.create(
			Board, title="Board title must not be displayed", creator_id=creator.id
		)
		first = app.store.create(
			Pin,
			title="First pin",
			url="https://example.com/complete/path",
			creator_id=creator.id,
		)
		second = app.store.create(
			Pin,
			title="Second pin",
			url="https://second.example/resource",
			creator_id=creator.id,
		)
		app.store.create(
			Placement, pin_id=first.id, board_id=board.id, adder_id=creator.id
		)
		app.sign_in(creator)

		res = app.client.get("/pins/")

		assert_eq(res.status_code, 200)
		assert_that(first.title in res.text)
		assert_that(second.title in res.text)
		assert_that("1 board" in res.text)
		assert_that("No boards" in res.text)
		assert_that(board.title not in res.text)


def test_new_form_and_creation_allow_no_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		app.store.create(Board, title="Reading", creator_id=creator.id)
		app.sign_in(creator)

		form_res = app.client.get("/pins/new")
		create_res = app.client.post(
			"/pins/",
			form={"title": "Unfiled", "url": "https://example.com"},
		)
		pin = app.store.find_by(Pin, title="Unfiled")[0]

		assert_eq(form_res.status_code, 200)
		assert_that('name="return_to" value="/pins/"' in form_res.text)
		assert_eq(create_res.headers["Location"], "/pins/")
		assert_eq(app.store.find_by(Placement, pin_id=pin.id), [])


def test_owned_unfiled_pin_is_accessible_only_to_creator():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		stranger = app.store.create(User, name="Stranger")
		pin = app.store.create(
			Pin, title="Unfiled", url="https://example.com", creator_id=creator.id
		)

		app.sign_in(creator)
		creator_res = app.client.get(f"/pins/{pin.id}")
		assert_eq(creator_res.status_code, 200)
		assert_that("Not on any boards" in creator_res.text)
		assert_that("Added by" not in creator_res.text)
		app.sign_in(stranger)
		assert_eq(app.client.get(f"/pins/{pin.id}").status_code, 404)


def test_pin_update_preserves_placements_on_inaccessible_boards():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		hidden_creator = app.store.create(User, name="Hidden creator")
		visible = app.store.create(Board, title="Visible", creator_id=creator.id)
		hidden = app.store.create(Board, title="Secret", creator_id=hidden_creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://plato.stanford.edu/entries/sartre/",
			creator_id=creator.id,
		)
		visible_placement = app.store.create(
			Placement, pin_id=pin.id, board_id=visible.id, adder_id=creator.id
		)
		hidden_placement = app.store.create(
			Placement, pin_id=pin.id, board_id=hidden.id, adder_id=hidden_creator.id
		)
		app.sign_in(creator)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={"_method": "PUT", "title": "Changed", "url": pin.url},
		)

		assert_eq(res.status_code, 302)
		with assert_raises(NotFoundError):
			app.store.find_one(Placement, visible_placement.id)
		retained = app.store.find_one(Placement, hidden_placement.id)
		assert_eq(retained.id, hidden_placement.id)
		assert_eq(retained.created_at, hidden_placement.created_at)
		assert_eq(retained.adder_id, hidden_creator.id)


def test_owned_pin_hides_inaccessible_board_names_without_calling_it_unfiled():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		hidden_creator = app.store.create(User, name="Hidden creator")
		hidden = app.store.create(
			Board, title="Secret plans", creator_id=hidden_creator.id
		)
		pin = app.store.create(
			Pin, title="Owned pin", url="https://example.com", creator_id=creator.id
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=hidden.id, adder_id=hidden_creator.id
		)
		app.sign_in(creator)

		index_res = app.client.get("/pins/")
		show_res = app.client.get(f"/pins/{pin.id}")
		edit_res = app.client.get(f"/pins/{pin.id}/edit")

		assert_eq(index_res.status_code, 200)
		assert_that(hidden.title not in index_res.text)
		assert_that("1 board" in index_res.text)
		assert_that("No boards" not in index_res.text)
		for res in [show_res, edit_res]:
			assert_eq(res.status_code, 200)
			assert_that(hidden.title not in res.text)
			assert_that("Not on any boards" not in res.text)


def test_deletes_pin():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		pin = app.store.create(
			Pin, title="Unfiled", url="https://example.com", creator_id=creator.id
		)
		app.sign_in(creator)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={"_method": "DELETE"},
		)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], "/pins/")
		assert_eq(app.store.find_all(Pin), [])


def test_new_form_from_board_returns_to_board():
	with TestApplication() as app:
		creator = app.store.create(User, name="Creator")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		app.sign_in(creator)

		res = app.client.get(f"/pins/new?board_id={board.id}")

		assert_eq(res.status_code, 200)
		assert_that(f'name="return_to" value="/boards/{board.id}"' in res.text)
