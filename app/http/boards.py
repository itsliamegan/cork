from typing import Any, cast
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
	Pin,
	Placement,
	Share,
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

	users = [user for user in store.find_all(User) if user.id != owner_id]
	users.sort(key=lambda user: user.name.casefold())
	return users


def index(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	access = Access(store, user)
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
	auth = ctx.get(Authenticator)
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	form, errors = BoardForm.validate(req.input)
	if "user_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	sharable_users = _sharable_users(ctx, user.id)
	if not set(form.user_ids) <= {sharable.id for sharable in sharable_users}:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	if errors:
		submissions.flash(errors, req.input)
		return Response.redirect(urls.route("boards.new"))

	board = Board.create(
		store,
		user,
		title=form.title,
		users=[sharable for sharable in sharable_users if sharable.id in form.user_ids],
	)

	return Response.redirect(urls.route("boards.show", {"id": board.id}))


def new(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	submission = ctx.get(Submission)
	user = cast(User, auth.user)

	return views.render(
		"boards.new",
		{
			"owner": auth.user,
			"users": _sharable_users(ctx, user.id),
			"shared_user_ids": set(submission.value("user_ids", [])),
		},
	)


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	user = cast(User, auth.user)

	access = Access(store, user)
	board = access.find_board(id)
	placements = Placement.arrange(store, board)
	archivals = Archival.arrange(store, board, user)
	archivals_by_placement_id = {
		archival.placement_id: archival for archival in archivals
	}
	placements_by_id = {placement.id: placement for placement in placements}
	pin_ids = [placement.pin_id for placement in placements]
	pins_by_id = {pin.id: pin for pin in store.query(Pin).where_in(id=pin_ids).all()}

	def placement_row(placement: Placement) -> dict[str, Any]:
		return {"placement": placement, "pin": pins_by_id[placement.pin_id]}

	placement_rows = [
		placement_row(placement)
		for placement in placements
		if placement.id not in archivals_by_placement_id
	]
	archived_rows = [
		{"archival": archival, **placement_row(placements_by_id[archival.placement_id])}
		for archival in archivals
	]

	return views.render(
		"boards.show",
		{
			"access": access,
			"board": board,
			"placement_rows": placement_rows,
			"archived_rows": archived_rows,
		},
	)


def edit(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	submission = ctx.get(Submission)
	user = cast(User, auth.user)

	access = Access(store, user)
	board = access.find_board(id)
	if not board.is_editable_by(access):
		raise NotPermitted(board)
	shared_user_ids = [
		share.user_id for share in store.find_by(Share, board_id=board.id)
	]

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
	auth = ctx.get(Authenticator)
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	access = Access(store, user)
	board = access.find_board(id)
	form, errors = BoardForm.validate(req.input)
	if "user_ids" in errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	sharable_users = _sharable_users(ctx, board.creator_id)
	if not set(form.user_ids) <= {sharable.id for sharable in sharable_users}:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	if errors:
		submissions.flash(errors, req.input)
		return Response.redirect(urls.route("boards.edit", {"id": board.id}))

	board.edit(
		store,
		access,
		title=form.title,
		users=[sharable for sharable in sharable_users if sharable.id in form.user_ids],
	)

	return_to = _board_return_url(ctx, form.return_to, board.id)
	return Response.redirect(return_to)


def delete(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)
	user = cast(User, auth.user)

	access = Access(store, user)
	board = access.find_board(id)
	board.delete(store, access)

	return Response.redirect(urls.route("boards.index"))
