from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Form
from helios.http import Request, Response, Status
from helios.routing import URLs

from app import Access, Archival, User


class ArchivalForm(Form):
	placement_id: UUID


def create(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	flash = context.get(Flashes)
	urls = context.get(URLs)

	form, errors = ArchivalForm.validate(request.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	access = Access(store, auth.user)
	placement = access.find_placement(form.placement_id)
	store.load(placement, "pin")

	archival = Archival.create(store, placement, auth.user)
	flash["archived"] = {"archival_id": str(archival.id), "title": placement.pin.title}
	return Response.redirect(urls.route("boards.show", {"id": placement.board_id}))


def delete(request: Request, context: Context, id: UUID) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	urls = context.get(URLs)

	access = Access(store, auth.user)
	archival = access.find_archival(id)
	store.load(archival, "placement")
	placement = archival.placement
	store.delete(archival)

	return Response.redirect(urls.route("boards.show", {"id": placement.board_id}))
