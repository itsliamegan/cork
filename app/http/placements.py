from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.http import Request, Response
from helios.routing import URLs

from app import Access, User


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	urls = ctx.get(URLs)

	access = Access(store, auth.user)
	placement = access.find_placement(id)
	store.load(placement, "pin", "board")
	placement.remove(store, access, placement.pin, placement.board)

	return Response.redirect(urls.route("boards.show", {"id": placement.board_id}))
