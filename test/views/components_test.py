from uuid import uuid4

from helios.view import Attributes, Engine
from luna.test.assertion import assert_not, assert_raises, assert_that

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
		link = ExternalLink(url="https://example.com", new_tab=True)

		html = engine.render(link)

		assert_that('target="_blank"' in html)
		assert_that('rel="noopener noreferrer"' in html)


def test_external_link_in_same_tab_sets_no_target():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		link = ExternalLink(url="https://example.com")

		html = engine.render(link)

		assert_not("target=" in html)
		assert_not("rel=" in html)


def test_external_link_refuses_a_caller_target():
	with assert_raises(TypeError):
		ExternalLink(
			url="https://example.com",
			new_tab=True,
			attributes=Attributes(target="_self"),
		)


def test_external_link_without_content_shows_its_url():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		link = ExternalLink(url="https://example.com/sartre")

		html = engine.render(link)

		assert_that(">https://example.com/sartre</a>" in html)


def test_pin_link_with_url_opens_the_url():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		pin = Pin(title="Sartre", url="https://sartre.example", creator_id=uuid4())
		link = PinLink(pin=pin, new_tab=True)

		html = engine.render(link)

		assert_that('href="https://sartre.example"' in html)
		assert_that('target="_blank"' in html)


def test_pin_link_without_url_opens_the_pin_in_the_same_tab():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		pin = Pin(title="Sartre", creator_id=uuid4())
		link = PinLink(pin=pin, new_tab=True)

		html = engine.render(link)

		assert_that(f'href="/pins/{pin.id}"' in html)
		assert_not("target=" in html)
		assert_not("rel=" in html)


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

		assert_that('command="show-modal" commandfor="pin-delete-dialog"' in html)
		assert_that('<dialog id="pin-delete-dialog"' in html)
		assert_that('form="pin-delete-form"' in html)
		assert_that('<form id="pin-delete-form" action="/pins/1"' in html)
		assert_that('name="_method" value="DELETE"' in html)
		assert_that("Delete this pin?" in html)


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

		assert_that(">Private</span>" in html)
		assert_that(">Shared · bob, Carmen</span>" in html)


def test_board_chips_mark_an_unfiled_pin():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		chips = BoardChips(boards=[], is_unfiled=True)

		html = engine.render(chips)

		assert_that("Not on any boards" in html)


def test_board_chips_without_boards_leave_a_filed_pin_unmarked():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		chips = BoardChips(boards=[], is_unfiled=False)

		html = engine.render(chips)

		assert_not("Not on any boards" in html)


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

		assert_that(f'href="/boards/{board.id}/edit">Edit</a>' in creator_html)
		assert_that(f'action="/boards/{board.id}"' in creator_html)
		assert_not('class="board-actions"' in participant_html)


def test_placement_menu_offers_edit_only_to_the_pins_creator():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		creator = app.store.create(User, name="Creator")
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=creator.id
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

		assert_that(f'href="/pins/{pin.id}">View</a>' in creator_html)
		assert_that(f'href="/pins/{pin.id}/edit">Edit</a>' in creator_html)
		assert_that(f'href="/pins/{pin.id}">View</a>' in reader_html)
		assert_not(">Edit</a>" in reader_html)


def test_placement_menu_offers_remove_only_when_allowed():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		creator = app.store.create(User, name="Creator")
		adder = app.store.create(User, name="Adder")
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=creator.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=creator.id
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

		assert_that(f'action="/placements/{placement.id}"' in removable_html)
		assert_not(f'action="/placements/{placement.id}"' in fixed_html)


def test_placement_item_archives_its_placement():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=reader.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(app.store, pin, board, reader)
		app.store.load(placement, "pin", "board")
		item = PlacementItem(
			placement=placement,
			access=Access(app.store, reader),
			preferences=Preferences(),
		)

		html = engine.render(item)

		assert_that('<form action="/archivals/" method="POST">' in html)
		assert_that(f'name="placement_id" value="{placement.id}"' in html)


def test_archival_item_unarchives_its_archival():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=reader.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
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

		assert_that(f'<form action="/archivals/{archival.id}" method="POST">' in html)
		assert_that('name="_method" value="DELETE"' in html)


def test_placement_item_opens_its_pin_in_a_new_tab_when_set():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		reader = app.store.create(User, name="Reader")
		board = app.store.create(Board, title="Reading", creator_id=reader.id)
		pin = app.store.create(
			Pin, title="Sartre", url="https://sartre.example", creator_id=reader.id
		)
		placement = Placement.create(app.store, pin, board, reader)
		app.store.load(placement, "pin", "board")
		item = PlacementItem(
			placement=placement,
			access=Access(app.store, reader),
			preferences=Preferences(open_in_new_tab=True),
		)

		html = engine.render(item)

		assert_that('target="_blank"' in html)
