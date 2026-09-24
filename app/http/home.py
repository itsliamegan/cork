from helios.app import Context
from helios.http import Request, Response
from helios.routing import URLs


def show(req: Request, ctx: Context) -> Response:
	urls = ctx.get(URLs)
	return Response.redirect(urls.route("boards.index"))
