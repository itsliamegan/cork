from helios.app import Context
from helios.http import Request, Response, URL


def show(req: Request, ctx: Context) -> Response:
	return Response.redirect(URL("/boards/"))
