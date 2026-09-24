from dataclasses import dataclass

from helios.view import Component


@dataclass
class ReorderHandle(Component):
	template = "components.reorder_handle"
