from typing import Literal

from helios.view import Component


class Icon(Component):
	template = "components.icon"

	name: Literal["archive", "drag", "overflow"]
