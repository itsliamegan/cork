from uuid import UUID

from lux.app import Context
from lux.http import Request, Response, URL

from app.data import Pin

def store(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = ctx.store.find_one(Pin, id)
	pin.hidden = True
	return Response.redirect(URL("/"))

def destroy(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = ctx.store.find_one(Pin, id)
	pin.hidden = False
	return Response.redirect(URL("/"))
