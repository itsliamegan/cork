from helios.database import Registry

from app import invite, recovery
from app.access import Access
from app.archival import Archival
from app.board import Board
from app.invite import Invite
from app.move import Move
from app.ordering import Ordering
from app.ownership import Ownership
from app.pin import Pin
from app.placement import Placement
from app.preferences import Preferences
from app.recovery import Recovery
from app.share import Share
from app.user import User

__all__ = [
	"Access",
	"Archival",
	"Board",
	"Invite",
	"Move",
	"Ordering",
	"Ownership",
	"Pin",
	"Placement",
	"Preferences",
	"Recovery",
	"Share",
	"User",
	"registry",
]


def registry() -> Registry:
	registry = Registry()

	registry.model(Archival)
	registry.model(Board)
	registry.model(Invite)
	registry.model(Ordering)
	registry.model(Pin)
	registry.model(Placement)
	registry.model(Recovery)
	registry.model(Share)
	registry.model(User)

	registry.codec(invite.Codec())
	registry.codec(recovery.Codec())

	return registry
