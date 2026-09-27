import json

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

		res = app.client.post(f"/placements/{placement.id}/archival")

		session_id = app.client.get_cookie("session_id").value
		session = json.loads(app.sessions_file.read_text())[session_id]
		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(
			session["items"]["_flash"]["archived"],
			{"placement_id": str(placement.id), "title": "Sartre"},
		)
		assert_eq(
			[
				(archival.placement_id, archival.user_id)
				for archival in app.store.find_all(Archival)
			],
			[(placement.id, recipient.id)],
		)


def test_archiving_an_archived_pin_keeps_it_archived():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.archive(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post(f"/placements/{placement.id}/archival")

		assert_eq(res.status_code, 302)
		assert_eq(
			[archival.id for archival in app.store.find_all(Archival)],
			[archival.id],
		)


def test_unarchive_redirects_to_the_board():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		Archival.archive(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{placement.id}/archival",
			form={"_method": "DELETE"},
		)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(app.store.find_all(Archival), [])


def test_unarchive_from_the_archived_section_redirects_to_it():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		Archival.archive(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{placement.id}/archival",
			form={"_method": "DELETE", "section": "archived"},
		)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}#archived")
		assert_eq(app.store.find_all(Archival), [])


def test_outsider_cannot_archive_or_unarchive():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		outsider = app.store.create(User, name="Outsider")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.archive(app.store, placement, owner)
		app.sign_in(outsider)

		create_res = app.client.post(f"/placements/{placement.id}/archival")
		delete_res = app.client.post(
			f"/placements/{placement.id}/archival",
			form={"_method": "DELETE"},
		)

		assert_eq(create_res.status_code, 404)
		assert_eq(delete_res.status_code, 404)
		assert_eq(
			[archival.id for archival in app.store.find_all(Archival)],
			[archival.id],
		)


def test_unarchive_rejects_an_unknown_section():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		archival = Archival.archive(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{placement.id}/archival",
			form={"_method": "DELETE", "section": "pins"},
		)

		assert_eq(res.status_code, 400)
		assert_eq(
			[archival.id for archival in app.store.find_all(Archival)],
			[archival.id],
		)


def test_unarchive_from_the_archived_section_streams_under_turbo():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		Archival.archive(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{placement.id}/archival",
			form={"_method": "DELETE", "section": "archived"},
			headers={"Accept": "text/vnd.turbo-stream.html, text/html"},
		)

		assert_eq(res.status_code, 200)
		assert_eq(res.headers["Content-Type"], "text/vnd.turbo-stream.html")
		assert_eq(app.store.find_all(Archival), [])


def test_unarchive_from_the_notice_redirects_under_turbo():
	with TestApplication() as app:
		owner = app.store.create(User, name="Owner")
		board = app.store.create(Board, title="Reading", creator_id=owner.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=owner.id
		)
		placement = Placement.create(app.store, pin, board, owner)
		Archival.archive(app.store, placement, owner)
		app.sign_in(owner)

		res = app.client.post(
			f"/placements/{placement.id}/archival",
			form={"_method": "DELETE"},
			headers={"Accept": "text/vnd.turbo-stream.html, text/html"},
		)

		assert_eq(res.status_code, 302)
		assert_eq(res.headers["Location"], f"/boards/{board.id}")
		assert_eq(app.store.find_all(Archival), [])
