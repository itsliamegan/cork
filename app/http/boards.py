from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Form, Rules, Submission, Submissions
from helios.form.rule import Distinct
from helios.http import Request, Response, Status, URL
from helios.routing import URLs
from helios.view import Views

from app import (
	Access,
	Archival,
	Board,
	Ordering,
	Placement,
	User,
)
from app.access import NotPermitted


class BoardForm(Form):
	rules = Rules({"user_ids": [Distinct()]})

	title: str
	user_ids: list[UUID] = []
	return_to: str | None = None


def _board_return_url(ctx: Context, raw_url: str | None, id: UUID) -> URL:
	urls = ctx.get(URLs)

	match = urls.match(raw_url)
	if match is not None and match.route.name == "boards.index":
		return urls.route("boards.index")
	else:
		return urls.route("boards.show", {"id": id})


def _sharable_users(ctx: Context, owner_id: UUID) -> list[User]:
	store = ctx.get(Store)

	users = store.query(User).where_not({"id": owner_id}).all()
	users.sort(key=lambda user: user.name.casefold())
	return users


def index(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)

	access = Access(store, auth.user)
	private, shared = Ordering.arrange(store, access)

	return views.render(
		"boards.index",
		{
			"access": access,
			"private": private,
			"shared": shared,
		},
	)


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)

	form, errors = BoardForm.validate(req.input)
	if "user_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	sharable_users = _sharable_users(ctx, auth.user.id)
	if not set(form.user_ids) <= {user.id for user in sharable_users}:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	if errors:
		submissions.flash(errors, req.input)
		return Response.redirect(urls.route("boards.new"))

	board = Board.create(
		store,
		auth.user,
		title=form.title,
		users=[user for user in sharable_users if user.id in form.user_ids],
	)

	return Response.redirect(urls.route("boards.show", {"id": board.id}))


def new(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)
	submission = ctx.get(Submission)

	return views.render(
		"boards.new",
		{
			"owner": auth.user,
			"users": _sharable_users(ctx, auth.user.id),
			"shared_user_ids": set(submission.value("user_ids", [])),
		},
	)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)

	access = Access(store, auth.user)
	board = access.find_board(id)
	archivals = Archival.arrange(store, board, auth.user)
	store.load(archivals, "placement.pin", "placement.board")
	archived_placement_ids = {archival.placement_id for archival in archivals}
	placements = [
		placement
		for placement in Placement.arrange(store, board)
		if placement.id not in archived_placement_ids
	]
	store.load(placements, "pin", "board")

	return views.render(
		"boards.show",
		{
			"access": access,
			"board": board,
			"placements": placements,
			"archivals": archivals,
		},
	)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	views = ctx.get(Views)
	submission = ctx.get(Submission)

	access = Access(store, auth.user)
	board = access.find_board(id)
	if not board.is_editable_by(access):
		raise NotPermitted(board)
	store.load(board, "shares")
	shared_user_ids = [share.user_id for share in board.shares]

	return views.render(
		"boards.edit",
		{
			"board": board,
			"owner": auth.user,
			"users": _sharable_users(ctx, board.creator_id),
			"shared_user_ids": set(submission.value("user_ids", shared_user_ids)),
			"return_to": _board_return_url(ctx, req.referrer, board.id),
		},
	)


def update(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)

	access = Access(store, auth.user)
	board = access.find_board(id)
	form, errors = BoardForm.validate(req.input)
	if "user_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	sharable_users = _sharable_users(ctx, board.creator_id)
	if not set(form.user_ids) <= {user.id for user in sharable_users}:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	if errors:
		submissions.flash(errors, req.input)
		return Response.redirect(urls.route("boards.edit", {"id": board.id}))

	board.edit(
		store,
		access,
		title=form.title,
		users=[user for user in sharable_users if user.id in form.user_ids],
	)

	return_to = _board_return_url(ctx, form.return_to, board.id)
	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator[User])
	urls = ctx.get(URLs)

	access = Access(store, auth.user)
	board = access.find_board(id)
	board.delete(store, access)

	return Response.redirect(urls.route("boards.index"))
