from uuid import uuid4

from helios.http import URL
from helios.view import Attributes, Engine
from luna.test.assertion import assert_in, assert_not_in, assert_raises

from app import Access, Archival, Board, Pin, Placement, Preferences, Share, User
from app.views.archivals.item import ArchivalItem
from app.views.boards.chips import BoardChips
from app.views.boards.item import BoardItem
from app.views.components.confirm_button import ConfirmButton
from app.views.components.external_link import ExternalLink
from app.views.pins.link import PinLink
from app.views.pins.placements import PinPlacements
from app.views.placements.item import PlacementItem
from app.views.placements.menu import PlacementMenu
from test.support import TestApplication


def test_external_link_in_new_tab_withholds_the_opener():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		link = ExternalLink(url=URL.parse("https://example.com"), new_tab=True)

		html = engine.render(link)

		assert_in('target="_blank"', html)
		assert_in('rel="noopener noreferrer"', html)


def test_external_link_in_same_tab_sets_no_target():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		link = ExternalLink(url=URL.parse("https://example.com"))

		html = engine.render(link)

		assert_not_in("target=", html)
		assert_not_in("rel=", html)


def test_external_link_refuses_a_caller_target():
	with assert_raises(TypeError):
		ExternalLink(
			url=URL.parse("https://example.com"),
			new_tab=True,
			attributes=Attributes(target="_self"),
		)


def test_external_link_without_content_shows_its_url():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		link = ExternalLink(url=URL.parse("https://example.com/sartre"))

		html = engine.render(link)

		assert_in(">https://example.com/sartre</a>", html)


def test_pin_link_with_url_opens_the_url():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		pin = Pin(
			title="Sartre", url=URL.parse("https://sartre.example"), creator_id=uuid4()
		)
		link = PinLink(pin=pin, new_tab=True)

		html = engine.render(link)

		assert_in('href="https://sartre.example"', html)
		assert_in('target="_blank"', html)


def test_pin_link_without_url_opens_the_pin_in_the_same_tab():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		pin = Pin(title="Sartre", creator_id=uuid4())
		link = PinLink(pin=pin, new_tab=True)

		html = engine.render(link)

		assert_in(f'href="/pins/{pin.id}"', html)
		assert_not_in("target=", html)
		assert_not_in("rel=", html)


def test_confirm_button_opens_the_dialog_it_renders():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		button = ConfirmButton(
			name="pin-delete",
			action="/pins/1",
			confirm="Delete",
			message="Delete this pin?",
			method="DELETE",
		)

		html = engine.render(button)

		assert_in('command="show-modal" commandfor="pin-delete-dialog"', html)
		assert_in('<dialog id="pin-delete-dialog"', html)
		assert_in('form="pin-delete-form"', html)
		assert_in('<form id="pin-delete-form" action="/pins/1"', html)
		assert_in('name="_method" value="DELETE"', html)
		assert_in("Delete this pin?", html)


def test_pin_placements_label_private_and_shared_boards():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		viewer = app.store.create(User, name="Viewer")
		capitalized_participant = app.store.create(User, name="Carmen")
		lowercase_participant = app.store.create(User, name="bob")
		notes = app.store.create(Board, title="Notes", creator_id=viewer.id)
		reading = app.store.create(Board, title="Reading", creator_id=viewer.id)
		for participant in [capitalized_participant, lowercase_participant]:
			app.store.create(Share, board_id=reading.id, user_id=participant.id)
		boards = [notes, reading]
		app.store.load(boards, "creator", "shares.user")
		placements = PinPlacements(
			boards=boards,
			viewer=viewer,
			selected_board_ids=set(),
		)

		html = engine.render(placements)

		assert_in(">Private</span>", html)
		assert_in(">Shared · bob, Carmen</span>", html)


def test_board_chips_mark_an_unfiled_pin():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		chips = BoardChips(boards=[], is_unfiled=True)

		html = engine.render(chips)

		assert_in("Not on any boards", html)


def test_board_chips_without_boards_leave_a_filed_pin_unmarked():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		chips = BoardChips(boards=[], is_unfiled=False)

		html = engine.render(chips)

		assert_not_in("Not on any boards", html)


def test_board_item_offers_its_menu_only_to_the_boards_creator():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		creator = app.store.create(User, name="Creator")
		participant = app.store.create(User, name="Participant")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)

		creator_html = engine.render(
			BoardItem(board=board, access=Access(app.store, creator))
		)
		participant_html = engine.render(
			BoardItem(board=board, access=Access(app.store, participant))
		)

		assert_in(f'href="/boards/{board.id}/edit">Edit</a>', creator_html)
		assert_in(f'action="/boards/{board.id}"', creator_html)
		assert_not_in('class="board-actions"', participant_html)


def test_placement_menu_offers_edit_only_to_the_pins_creator():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		creator = app.store.create(User, name="Creator")
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://sartre.example"),
			creator_id=creator.id,
		)
		placement = Placement.create(app.store, pin, board, creator)
		app.store.load(placement, "pin", "board")

		creator_html = engine.render(
			PlacementMenu(
				placement=placement,
				access=Access(app.store, creator),
			)
		)
		reader_html = engine.render(
			PlacementMenu(
				placement=placement,
				access=Access(app.store, reader),
			)
		)

		assert_in(f'href="/pins/{pin.id}">View</a>', creator_html)
		assert_in(f'href="/pins/{pin.id}/edit">Edit</a>', creator_html)
		assert_in(f'href="/pins/{pin.id}">View</a>', reader_html)
		assert_not_in(">Edit</a>", reader_html)


def test_placement_menu_offers_remove_only_when_allowed():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		creator = app.store.create(User, name="Creator")
		adder = app.store.create(User, name="Adder")
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://sartre.example"),
			creator_id=creator.id,
		)
		placement = Placement.create(app.store, pin, board, adder)
		app.store.load(placement, "pin", "board")

		removable_html = engine.render(
			PlacementMenu(
				placement=placement,
				access=Access(app.store, adder),
			)
		)
		fixed_html = engine.render(
			PlacementMenu(
				placement=placement,
				access=Access(app.store, reader),
			)
		)

		assert_in(f'action="/placements/{placement.id}"', removable_html)
		assert_not_in(f'action="/placements/{placement.id}"', fixed_html)


def test_placement_item_archives_its_placement():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=reader.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://sartre.example"),
			creator_id=reader.id,
		)
		placement = Placement.create(app.store, pin, board, reader)
		app.store.load(placement, "pin", "board")
		item = PlacementItem(
			placement=placement,
			access=Access(app.store, reader),
			preferences=Preferences(),
		)

		html = engine.render(item)

		assert_in('<form action="/archivals/" method="POST">', html)
		assert_in(f'name="placement_id" value="{placement.id}"', html)


def test_archival_item_unarchives_its_archival():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=reader.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://sartre.example"),
			creator_id=reader.id,
		)
		placement = Placement.create(app.store, pin, board, reader)
		archival = Archival.create(app.store, placement, reader)
		app.store.load(archival, "placement.pin", "placement.board")
		item = ArchivalItem(
			archival=archival,
			access=Access(app.store, reader),
			preferences=Preferences(),
		)

		html = engine.render(item)

		assert_in(f'<form action="/archivals/{archival.id}" method="POST">', html)
		assert_in('name="_method" value="DELETE"', html)


def test_placement_item_opens_its_pin_in_a_new_tab_when_set():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=reader.id)
		pin = app.store.create(
			Pin,
			title="Sartre",
			url=URL.parse("https://sartre.example"),
			creator_id=reader.id,
		)
		placement = Placement.create(app.store, pin, board, reader)
		app.store.load(placement, "pin", "board")
		item = PlacementItem(
			placement=placement,
			access=Access(app.store, reader),
			preferences=Preferences(open_in_new_tab=True),
		)

		html = engine.render(item)

		assert_in('target="_blank"', html)
