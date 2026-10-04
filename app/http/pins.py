from uuid import UUID

from helios import http
from helios.app import Context
from helios.auth import Authenticator
from helios.database import NotFoundError, Store
from helios.form import Form, Rules, Submission, Submissions
from helios.form.rule import Distinct, Rule, RuleError
from helios.http import Request, Response, Status, URL
from helios.routing import URLs
from helios.view import Views

from app import Access, Board, Ownership, Pin, Placement, User
from app.access import NotPermitted


class WebURL(Rule[URL]):
	name = "web_url"
	schemes = {"http", "https"}

	def check(self, value: URL):
		if value.scheme not in self.schemes:
			raise RuleError("must be an http:// or https:// URL")


class PinForm(Form):
	rules = Rules({"url": [WebURL()], "board_ids": [Distinct()]})
	messages = {
		"url.invalid": "URL must be an http:// or https:// address.",
		"url.web_url": "URL must be an http:// or https:// address.",
	}

	title: str
	url: URL | None = None
	note: str = ""
	board_ids: list[UUID] = []
	return_to: str | None = None


def _referring_board_id(
	context: Context,
	raw_url: str | None,
	placements: list[Placement],
) -> UUID | None:
	urls = context.get(URLs)

	match = urls.match(raw_url)
	if match is None or match.route.name != "boards.show":
		return None
	for placement in placements:
		if placement.board_id == match.parameters["id"]:
			return placement.board_id
	return None


def _pin_return_url(
	context: Context,
	raw_url: str | None,
	pin: Pin,
	placements: list[Placement],
) -> URL:
	urls = context.get(URLs)

	match = urls.match(raw_url)
	if match is not None and match.route.name == "pins.index":
		return urls.route("pins.index")
	board_id = _referring_board_id(context, raw_url, placements)
	if board_id is None:
		return urls.route("pins.show", {"id": pin.id})
	return urls.route("boards.show", {"id": board_id})


def find_placeable_boards(context: Context) -> list[Board]:
	store = context.get(Store)
	auth = context.get(Authenticator[User])

	boards = Access(store, auth.user).find_boards()
	store.load(boards, "creator", "shares.user")
	return boards


def index(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	views = context.get(Views)

	pins = Ownership(store, auth.user).find_pins()
	pins.sort(key=lambda pin: pin.created_at, reverse=True)
	store.load(pins, "placements")

	return views.render(
		"pins.index",
		{
			"pins": pins,
		},
	)


def create(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	submissions = context.get(Submissions)
	urls = context.get(URLs)

	form, errors = PinForm.validate(request.input)
	if "board_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	access = Access(store, auth.user)
	try:
		boards = [access.find_board(board_id) for board_id in form.board_ids]
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	if errors:
		submissions.flash(errors, request.input)
		match = urls.match(form.return_to) if "return_to" not in errors else None
		if match is not None and match.route.name == "boards.show":
			query = {"board_id": str(match.parameters["id"])}
			return Response.redirect(urls.route("pins.new", query=query))
		else:
			return Response.redirect(urls.route("pins.new"))

	Pin.create(
		store,
		access,
		title=form.title,
		url=form.url,
		note=form.note,
		boards=boards,
	)

	match = urls.match(form.return_to)
	if (
		match is not None
		and match.route.name == "boards.show"
		and match.parameters["id"] in {board.id for board in boards}
	):
		return Response.redirect(urls.route("boards.show", match.parameters))
	else:
		return Response.redirect(urls.route("pins.index"))


def new(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	views = context.get(Views)
	submission = context.get(Submission)
	urls = context.get(URLs)

	access = Access(store, auth.user)
	board_id = request.url.query.first("board_id")
	if board_id is not None:
		try:
			id = UUID(board_id)
		except ValueError:
			raise http.error.NotFoundError()
		board = access.find_board(id)
		selected_board_ids = [board.id]
		return_to = urls.route("boards.show", {"id": board.id})
	else:
		board = None
		selected_board_ids = []
		return_to = urls.route("pins.index")

	return views.render(
		"pins.new",
		{
			"originating_board": board,
			"placeable_boards": find_placeable_boards(context),
			"selected_board_ids": set(
				submission.value("board_ids", selected_board_ids)
			),
			"return_to": return_to,
		},
	)


def show(request: Request, context: Context, id: UUID) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	views = context.get(Views)

	access = Access(store, auth.user)
	pin = access.find_pin(id)
	store.load(pin, "creator", "placements")
	placements = pin.find_accessible_placements(store, access)
	store.load(placements, "board", "adder")
	adder = Placement.find_adder(
		placements,
		_referring_board_id(context, request.referrer, placements),
	)
	return views.render(
		"pins.show",
		{
			"access": access,
			"pin": pin,
			"accessible_boards": [placement.board for placement in placements],
			"adder": adder,
		},
	)


def edit(request: Request, context: Context, id: UUID) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	views = context.get(Views)
	submission = context.get(Submission)

	access = Access(store, auth.user)
	pin = access.find_pin(id)
	if not pin.is_editable_by(access):
		raise NotPermitted(pin)
	placements = pin.find_accessible_placements(store, access)
	selected_board_ids = [placement.board_id for placement in placements]

	return views.render(
		"pins.edit",
		{
			"pin": pin,
			"placeable_boards": find_placeable_boards(context),
			"selected_board_ids": set(
				submission.value("board_ids", selected_board_ids)
			),
			"return_to": _pin_return_url(
				context,
				request.referrer,
				pin,
				placements,
			),
		},
	)


def update(request: Request, context: Context, id: UUID) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	submissions = context.get(Submissions)
	urls = context.get(URLs)

	access = Access(store, auth.user)
	pin = access.find_pin(id)

	form, errors = PinForm.validate(request.input)
	if "board_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	try:
		boards = [access.find_board(board_id) for board_id in form.board_ids]
	except NotFoundError:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	if errors:
		submissions.flash(errors, request.input)
		return Response.redirect(urls.route("pins.edit", {"id": pin.id}))

	return_to = _pin_return_url(
		context,
		form.return_to,
		pin,
		pin.find_accessible_placements(store, access),
	)
	pin.edit(
		store,
		access,
		title=form.title,
		url=form.url,
		note=form.note,
		boards=boards,
	)

	return Response.redirect(return_to)


def delete(request: Request, context: Context, id: UUID) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	urls = context.get(URLs)

	access = Access(store, auth.user)
	pin = access.find_pin(id)
	pin.delete(store, access)

	return Response.redirect(urls.route("pins.index"))
