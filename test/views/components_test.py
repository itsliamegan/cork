from uuid import uuid4

from helios.view import Attributes, Engine
from luna.test.assertion import assert_not, assert_raises, assert_that

from app import Board, User
from app.views.boards.chips import BoardChips
from app.views.components.confirm_button import ConfirmButton
from app.views.components.external_link import ExternalLink
from app.views.pins.placements import PinPlacements, PlacementOption
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
		viewer_id = uuid4()
		capitalized_participant = User(name="Carmen")
		lowercase_participant = User(name="bob")
		placements = PinPlacements(
			options=[
				PlacementOption(
					board=Board(title="Notes", creator_id=viewer_id),
					others=[],
				),
				PlacementOption(
					board=Board(title="Reading", creator_id=viewer_id),
					others=[capitalized_participant, lowercase_participant],
				),
			],
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
