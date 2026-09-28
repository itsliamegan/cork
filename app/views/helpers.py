from helios.http import URL
from helios.view import Helpers


def site(url: str) -> str:
	try:
		host = URL(url).host
	except ValueError:
		return url
	return host.removeprefix("www.") if host else url


helpers = Helpers(filters={"site": site})
