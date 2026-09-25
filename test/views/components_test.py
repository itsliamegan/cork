from helios.view import Attributes, Engine
from luna.test.assertion import assert_not, assert_raises, assert_that

from app.views.components.external_link import ExternalLink
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
