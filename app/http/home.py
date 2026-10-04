from helios.app import Context
from helios.http import Request, Response
from helios.routing import URLs


def show(request: Request, context: Context) -> Response:
	urls = context.get(URLs)

	return Response.redirect(urls.route("boards.index"))
