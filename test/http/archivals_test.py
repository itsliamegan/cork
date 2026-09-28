import json
from uuid import uuid4

from luna.test.assertion import assert_eq

from app import Archival, Board, Pin, Placement, Share, User
from test.support import TestApplication


def test_archive_redirects_to_the_board_with_a_flash():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		recipient = app.store.create(User, name="Recipient")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		Share.replace(app.store, board, [recipient])
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		app.sign_in(recipient)

		res = app.client.post("/archivals/", form={"placement_id": str(placement.id)})

		session_id = app.client.get_cookie("session_id").value
		session = json.loads(app.sessions_file.read_text())[session_id]
		archivals = app.store.find_all(Archival)
		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(
			[(archival.placement_id, archival.user_id) for archival in archivals],
			[(placement.id, recipient.id)],
		)
		assert_eq(
			session["items"]["_flash"]["archived"],
			{"archival_id": str(archivals[0].id), "title": "Sartre"},
		)


def test_archiving_an_archived_pin_keeps_it_archived():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.create(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post("/archivals/", form={"placement_id": str(placement.id)})

		assert_eq(res.status_code, 302)
		assert_eq(
			[archival.id for archival in app.store.find_all(Archival)],
			[archival.id],
		)


def test_archive_rejects_a_missing_placement_id():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		app.sign_in(owner)

		res = app.client.post("/archivals/", form={})

		assert_eq(res.status_code, 400)
		assert_eq(app.store.find_all(Archival), [])


def test_outsider_cannot_archive():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		outsider = app.store.create(User, name="Outsider")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		app.sign_in(outsider)

		res = app.client.post("/archivals/", form={"placement_id": str(placement.id)})

		assert_eq(res.status_code, 404)
		assert_eq(app.store.find_all(Archival), [])


def test_unarchive_redirects_to_the_board():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.create(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post(f"/archivals/{archival.id}", form={"_method": "DELETE"})

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(app.store.find_all(Archival), [])


def test_unarchiving_twice_is_not_found():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.create(app.store, placement, owner)
		app.sign_in(owner)

		first = app.client.post(f"/archivals/{archival.id}", form={"_method": "DELETE"})
		second = app.client.post(
			f"/archivals/{archival.id}", form={"_method": "DELETE"}
		)

		assert_eq(first.status_code, 302)
		assert_eq(second.status_code, 404)


def test_cannot_unarchive_another_users_archival():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		recipient = app.store.create(User, name="Recipient")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		Share.replace(app.store, board, [recipient])
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.create(app.store, placement, recipient)
		app.sign_in(owner)

		res = app.client.post(f"/archivals/{archival.id}", form={"_method": "DELETE"})

		assert_eq(res.status_code, 404)
		assert_eq(
			[archival.id for archival in app.store.find_all(Archival)],
			[archival.id],
		)


def test_cannot_unarchive_on_a_board_no_longer_shared():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		recipient = app.store.create(User, name="Recipient")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		Share.replace(app.store, board, [recipient])
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.create(app.store, placement, recipient)
		Share.replace(app.store, board, [])
		app.sign_in(recipient)

		res = app.client.post(f"/archivals/{archival.id}", form={"_method": "DELETE"})

		assert_eq(res.status_code, 404)
		assert_eq(
			[archival.id for archival in app.store.find_all(Archival)],
			[archival.id],
		)


def test_unarchiving_an_unknown_archival_is_not_found():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		app.sign_in(owner)

		res = app.client.post(f"/archivals/{uuid4()}", form={"_method": "DELETE"})

		assert_eq(res.status_code, 404)
