from uuid import uuid4

from helios.database import NotFoundError
from luna.test.assertion import assert_eq, assert_raises, assert_that

from app.data import Board, Pin, Placement, Share, User, find_pin_placements
from test.support import TestApplication


def test_creates_pin_with_placements_for_selected_boards():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		app.sign_in(user)

		res = app.client.post(
			"/pins/",
			form={
				"title": "Stanford Entry on Sartre",
				"url": "https://plato.stanford.edu/entries/sartre/",
				"note": "Read the Negation section.",
				"board_id": [str(essays.id), str(reading.id), str(reading.id)],
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
		assert_eq({placement.adder_id for placement in placements}, {user.id})


def checkbox_is_checked(html: str, board_id) -> bool:
	checkbox = html[html.index(f'value="{board_id}"') :].split(">", maxsplit=1)[0]
	return "checked" in checkbox


def test_new_form_checks_originating_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		app.sign_in(user)

		res = app.client.get(f"/pins/new?board_id={reading.id}")

		assert_eq(res.status_code, 200)
		assert_that("No matching boards." in res.text)
		assert_that(checkbox_is_checked(res.text, reading.id))
		assert_that(not checkbox_is_checked(res.text, essays.id))


def test_new_form_rejects_inaccessible_boards():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		eve = app.store.create(User, name="Eve")
		hidden = app.store.create(Board, title="Hidden", creator_id=eve.id)
		app.sign_in(alice)

		hidden_res = app.client.get(f"/pins/new?board_id={hidden.id}")
		malformed_res = app.client.get("/pins/new?board_id=not-a-board")

		assert_eq(hidden_res.status_code, 404)
		assert_eq(malformed_res.status_code, 404)


def test_board_links_to_new_pin_form_for_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", creator_id=user.id)
		app.sign_in(user)

		res = app.client.get(f"/boards/{board.id}")

		assert_that(f'href="/pins/new?board_id={board.id}"' in res.text)


def test_edit_form_checks_each_placed_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		unread = app.store.create(Board, title="Unread", creator_id=user.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)
		for board in [reading, essays]:
			app.store.create(
				Placement, pin_id=pin.id, board_id=board.id, adder_id=user.id
			)
		app.sign_in(user)

		res = app.client.get(f"/pins/{pin.id}/edit")

		assert_eq(res.status_code, 200)
		assert_that("No matching boards." in res.text)
		for board in [reading, essays, unread]:
			assert_that(f'value="{board.id}"' in res.text)
		for board in [reading, essays]:
			assert_that(checkbox_is_checked(res.text, board.id))
		assert_that(not checkbox_is_checked(res.text, unread.id))


def test_board_picker_includes_only_accessible_boards():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		nadia = app.store.create(User, name="nadia")
		theo = app.store.create(User, name="Theo")
		carlos = app.store.create(User, name="Carlos")
		eve = app.store.create(User, name="Eve")
		mallory = app.store.create(User, name="Mallory")
		private = app.store.create(Board, title="Private", creator_id=alice.id)
		shared = app.store.create(Board, title="Shared", creator_id=alice.id)
		incoming = app.store.create(Board, title="Incoming", creator_id=carlos.id)
		hidden = app.store.create(Board, title="Hidden", creator_id=mallory.id)
		for board, user in [
			(shared, nadia),
			(shared, theo),
			(incoming, alice),
			(incoming, eve),
			(hidden, eve),
		]:
			app.store.create(Share, board_id=board.id, user_id=user.id)
		app.sign_in(alice)

		res = app.client.get(f"/pins/new?board_id={private.id}")

		assert_eq(res.status_code, 200)
		for board in [private, shared, incoming]:
			assert_that(f'value="{board.id}"' in res.text)
		assert_that(f'value="{hidden.id}"' not in res.text)


def test_update_adds_and_removes_placements_without_replacing_retained_placements():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		unread = app.store.create(Board, title="Unread", creator_id=user.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)
		retained = app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=user.id
		)
		removed = app.store.create(
			Placement, pin_id=pin.id, board_id=essays.id, adder_id=user.id
		)
		app.sign_in(user)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={
				"_method": "PUT",
				"title": "Updated Sartre",
				"url": "https://example.com/updated",
				"note": "Updated note",
				"board_id": [str(reading.id), str(unread.id)],
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
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		reading = app.store.create(Board, title="Reading", creator_id=alice.id)
		private = app.store.create(Board, title="Private", creator_id=bob.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)
		placement = app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=alice.id
		)
		app.sign_in(alice)

		for board_ids in [[str(uuid4())], [str(private.id)]]:
			res = app.client.post(
				"/pins/",
				form={
					"title": "New pin",
					"url": "https://new.example",
					"board_id": board_ids,
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
					"board_id": board_ids,
				},
			)
			assert_eq(res.status_code, 400)
			assert_eq(app.store.find_one(Pin, pin.id).title, "Sartre")
			assert_eq(app.store.find_one(Placement, placement.id).board_id, reading.id)


def test_access_to_any_placed_board_allows_pin_details():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		private = app.store.create(Board, title="Private", creator_id=alice.id)
		shared = app.store.create(Board, title="Shared", creator_id=alice.id)
		app.store.create(Share, board_id=shared.id, user_id=bob.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)
		for board in [private, shared]:
			app.store.create(
				Placement, pin_id=pin.id, board_id=board.id, adder_id=alice.id
			)
		app.sign_in(bob)

		assert_eq(app.client.get(f"/pins/{pin.id}").status_code, 200)


def test_unrelated_user_cannot_open_pin_details():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		board = app.store.create(Board, title="Reading", creator_id=alice.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)
		app.store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=alice.id)
		app.sign_in(bob)

		assert_eq(app.client.get(f"/pins/{pin.id}").status_code, 404)


def test_delete_removes_every_placement():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		reading = app.store.create(Board, title="Reading", creator_id=user.id)
		essays = app.store.create(Board, title="Essays", creator_id=user.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)
		for board in [reading, essays]:
			app.store.create(
				Placement, pin_id=pin.id, board_id=board.id, adder_id=user.id
			)
		app.sign_in(user)

		res = app.client.post(
			f"/pins/{pin.id}",
			form={"_method": "DELETE", "return_to": f"/boards/{essays.id}"},
		)

		assert_eq(res.headers["Location"], f"/boards/{essays.id}")
		assert_eq(app.store.find_all(Pin), [])
		assert_eq(app.store.find_all(Placement), [])


def test_pin_without_placements_is_unfiled():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)

		assert_eq(find_pin_placements(app.store, pin.id), [])


def test_pin_details_embed_frame_with_accessible_boards_and_actions():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		reading = app.store.create(Board, title="Reading", creator_id=alice.id)
		shared = app.store.create(Board, title="Shared", creator_id=alice.id)
		app.store.create(Share, board_id=shared.id, user_id=bob.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url="https://example.com/sartre",
			note="Read this closely.",
			creator_id=alice.id,
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=alice.id
		)
		app.store.create(Placement, pin_id=pin.id, board_id=shared.id, adder_id=bob.id)
		app.sign_in(bob)

		res = app.client.get(f"/pins/{pin.id}")

		assert_that("https://example.com/sartre" in res.text)


def test_pin_details_use_referring_board_placement_and_empty_note_state():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		reading = app.store.create(Board, title="Reading", creator_id=alice.id)
		essays = app.store.create(Board, title="Essays", creator_id=alice.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)
		app.store.create(
			Placement, pin_id=pin.id, board_id=reading.id, adder_id=alice.id
		)
		app.store.create(Placement, pin_id=pin.id, board_id=essays.id, adder_id=bob.id)
		app.sign_in(alice)

		res = app.client.get(
			f"/pins/{pin.id}", headers={"Referer": f"/boards/{essays.id}"}
		)

		assert_eq(res.status_code, 200)
		assert_that("Bob" in res.text)
		assert_that("No note." in res.text)
		assert_that(f'href="/pins/{pin.id}/edit"' in res.text)


def test_owned_pins_index_includes_unfiled_pins_and_hides_other_creators():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		shared = app.store.create(Board, title="Shared reading", creator_id=bob.id)
		app.store.create(Share, board_id=shared.id, user_id=alice.id)
		owned = app.store.create(
			Pin, title="Owned unfiled", url="https://owned.example", creator_id=alice.id
		)
		visible = app.store.create(
			Pin,
			title="Someone else's pin",
			url="https://other.example",
			creator_id=bob.id,
		)
		app.store.create(
			Placement, pin_id=visible.id, board_id=shared.id, adder_id=bob.id
		)
		app.sign_in(alice)

		res = app.client.get("/pins/")

		assert_eq(res.status_code, 200)
		assert_that(owned.title in res.text)
		assert_that("No boards" in res.text)
		assert_that(visible.title not in res.text)
		assert_that('href="/pins/new"' in res.text)


def test_pins_index_renders_search_control_and_complete_collection():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(
			Board, title="Board title must not be displayed", creator_id=user.id
		)
		first = app.store.create(
			Pin,
			title="First pin",
			url="https://example.com/complete/path",
			creator_id=user.id,
		)
		second = app.store.create(
			Pin,
			title="Second pin",
			url="https://second.example/resource",
			creator_id=user.id,
		)
		app.store.create(
			Placement, pin_id=first.id, board_id=board.id, adder_id=user.id
		)
		app.sign_in(user)

		res = app.client.get("/pins/")

		placeholder_position = res.text.index('placeholder="Search"')
		search_input = res.text[
			res.text.rindex("<input", 0, placeholder_position) : res.text.index(
				"\n\t\t>", placeholder_position
			)
		]
		assert_that('type="search"' in search_input)
		assert_that('aria-label="Search pins"' in search_input)
		assert_that("name=" not in search_input)
		assert_that(f'href="/pins/{first.id}"' in res.text)
		assert_that(f'href="/pins/{second.id}"' in res.text)
		assert_that("1 board" in res.text)
		assert_that("No boards" in res.text)
		assert_that(board.title not in res.text)
		assert_that("No matching pins." in res.text)
		assert_that("No pins yet." not in res.text)
		assert_that('rel="next"' not in res.text)


def test_empty_pins_index_distinguishes_collection_and_search_empty_states():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		app.sign_in(user)

		res = app.client.get("/pins/")

		assert_that("No pins yet." in res.text)
		assert_that("No matching pins." in res.text)


def test_new_form_and_creation_allow_no_board():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", creator_id=user.id)
		app.sign_in(user)

		form_res = app.client.get("/pins/new")
		create_res = app.client.post(
			"/pins/",
			form={"title": "Unfiled", "url": "https://example.com"},
		)
		pin = app.store.find_by(Pin, title="Unfiled")[0]

		assert_eq(form_res.status_code, 200)
		assert_that(not checkbox_is_checked(form_res.text, board.id))
		assert_that('name="return_to" value="/pins/"' in form_res.text)
		assert_eq(create_res.headers["Location"], "/pins/")
		assert_eq(app.store.find_by(Placement, pin_id=pin.id), [])


def test_owned_unfiled_pin_is_accessible_only_to_creator():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		pin = app.store.create(
			Pin, title="Unfiled", url="https://example.com", creator_id=alice.id
		)

		app.sign_in(alice)
		creator_res = app.client.get(f"/pins/{pin.id}")
		assert_eq(creator_res.status_code, 200)
		assert_that("Not on any boards" in creator_res.text)
		assert_that("Added by" not in creator_res.text)
		app.sign_in(bob)
		assert_eq(app.client.get(f"/pins/{pin.id}").status_code, 404)


def test_pin_update_preserves_placements_on_inaccessible_boards():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		visible = app.store.create(Board, title="Visible", creator_id=alice.id)
		hidden = app.store.create(Board, title="Secret", creator_id=bob.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=alice.id
		)
		visible_placement = app.store.create(
			Placement, pin_id=pin.id, board_id=visible.id, adder_id=alice.id
		)
		hidden_placement = app.store.create(
			Placement, pin_id=pin.id, board_id=hidden.id, adder_id=bob.id
		)
		app.sign_in(alice)

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
		assert_eq(retained.adder_id, bob.id)


def test_owned_pin_hides_inaccessible_board_names_without_calling_it_unfiled():
	with TestApplication() as app:
		alice = app.store.create(User, name="Alice")
		bob = app.store.create(User, name="Bob")
		hidden = app.store.create(Board, title="Secret plans", creator_id=bob.id)
		pin = app.store.create(
			Pin, title="Owned pin", url="https://example.com", creator_id=alice.id
		)
		app.store.create(Placement, pin_id=pin.id, board_id=hidden.id, adder_id=bob.id)
		app.sign_in(alice)

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
		user = app.store.create(User, name="Alice")
		pin = app.store.create(
			Pin, title="Unfiled", url="https://example.com", creator_id=user.id
		)
		app.sign_in(user)

		app.client.post(
			f"/pins/{pin.id}",
			form={"_method": "DELETE", "return_to": f"/pins/{pin.id}"},
		)

		assert_eq(app.store.find_all(Pin), [])


def test_pin_forms_keep_return_behavior_without_board_backlinks():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		board = app.store.create(Board, title="Reading", creator_id=user.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)
		app.store.create(Placement, pin_id=pin.id, board_id=board.id, adder_id=user.id)
		app.sign_in(user)

		new_res = app.client.get(f"/pins/new?board_id={board.id}")
		edit_res = app.client.get(f"/pins/{pin.id}/edit")

		assert_that("Board:" not in new_res.text and "Board:" not in edit_res.text)
		assert_that(checkbox_is_checked(new_res.text, board.id))
		assert_that(f'name="return_to" value="/boards/{board.id}"' in new_res.text)
		assert_that(f'href="/pins/{pin.id}"' in edit_res.text)
