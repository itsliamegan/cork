from helios.http import URL
from luna.test.assertion import assert_eq

from app.views.helpers import site


def test_site_shortens_to_hostname():
	url = URL.parse("https://plato.stanford.edu/entries/sartre/")

	shortened = site(url)

	assert_eq(shortened, "plato.stanford.edu")


def test_site_drops_www_prefix():
	url = URL.parse("https://www.example.com/articles")

	shortened = site(url)

	assert_eq(shortened, "example.com")


def test_site_falls_back_to_url_without_a_host():
	url = URL.parse("/entries/sartre")

	shortened = site(url)

	assert_eq(shortened, "/entries/sartre")
