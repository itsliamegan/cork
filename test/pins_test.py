from uuid import uuid4

from helios.data.store import NotFoundError
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

		res = app.client.get(f"/boards/{reading.id}/pins/new")

		assert_eq(res.status_code, 200)
		assert_that(checkbox_is_checked(res.text, reading.id))
		assert_that(not checkbox_is_checked(res.text, essays.id))


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

		res = app.client.get(f"/boards/{private.id}/pins/new")

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

		for board_ids in [[], [str(uuid4())], [str(private.id)]]:
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


def test_pin_without_placements_fails_clearly_as_invalid_data():
	with TestApplication() as app:
		user = app.store.create(User, name="Alice")
		pin = app.store.create(
			Pin, title="Sartre", url="https://example.com", creator_id=user.id
		)

		with assert_raises(ValueError) as raised:
			find_pin_placements(app.store, pin.id)

		assert_that(str(pin.id) in str(raised.exception))
