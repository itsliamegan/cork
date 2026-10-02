from helios.http import URL
from helios.view import Helpers


def site(url: URL) -> str:
	if url.host is None:
		return str(url)
	else:
		return url.host.removeprefix("www.")


helpers = Helpers(filters={"site": site})
