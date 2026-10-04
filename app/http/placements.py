from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.http import Request, Response
from helios.routing import URLs

from app import Access, User


def delete(request: Request, context: Context, id: UUID) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	urls = context.get(URLs)

	access = Access(store, auth.user)
	placement = access.find_placement(id)
	store.load(placement, "pin", "board")
	placement.remove(store, access)

	return Response.redirect(urls.route("boards.show", {"id": placement.board_id}))
