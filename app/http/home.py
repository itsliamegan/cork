from helios.app import Context
from helios.http import Request, Response

def show(req: Request, ctx: Context) -> Response:
	return Response.empty()
