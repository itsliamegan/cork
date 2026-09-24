from uuid import uuid4

from helios.view import Attributes, Engine
from luna.test.assertion import assert_not, assert_raises, assert_that

from app.data import Board, User
from app.views.boards.chips import BoardChips
from app.views.components.confirm_dialog import ConfirmDialog
from app.views.components.confirm_trigger import ConfirmTrigger
from app.views.components.external_link import ExternalLink
from app.views.pins.placements import BoardOption, PinPlacements
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


def test_confirm_trigger_opens_its_dialog_when_confirmation_is_required():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		dialog = ConfirmDialog(
			name="pin-delete",
			action="/pins/1",
			confirm="Delete",
			content="Delete this pin?",
			method="DELETE",
		)
		trigger = ConfirmTrigger(dialog=dialog)

		dialog_html = engine.render(dialog)
		trigger_html = engine.render(trigger)

		assert_that(f'id="{dialog.dialog_id}"' in dialog_html)
		assert_that(f'commandfor="{dialog.dialog_id}"' in trigger_html)
		assert_that(f'form="{dialog.form_id}"' in dialog_html)
		assert_that(f'<form id="{dialog.form_id}"' in dialog_html)
		assert_that('name="_method" value="DELETE"' in dialog_html)


def test_confirm_trigger_submits_directly_when_confirmation_is_not_required():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		dialog = ConfirmDialog(
			name="recovery",
			action="/recoveries/",
			confirm="Replace",
			content="Replace your recovery code?",
			required=False,
		)
		trigger = ConfirmTrigger(dialog=dialog)

		dialog_html = engine.render(dialog)
		trigger_html = engine.render(trigger)

		assert_not("<dialog" in dialog_html)
		assert_that(f'<form id="{dialog.form_id}"' in dialog_html)
		assert_that(f'form="{dialog.form_id}"' in trigger_html)
		assert_that('type="submit"' in trigger_html)


def test_pin_placements_label_private_and_shared_boards():
	with TestApplication() as app:
		engine = app.container.get(Engine)
		viewer_id = uuid4()
		carmen = User(name="Carmen")
		bob = User(name="bob")
		placements = PinPlacements(
			options=[
				BoardOption(
					board=Board(title="Notes", creator_id=viewer_id),
					shared_with=[],
				),
				BoardOption(
					board=Board(title="Reading", creator_id=viewer_id),
					shared_with=[carmen, bob],
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
