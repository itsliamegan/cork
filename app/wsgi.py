import helios.app
import helios.auth
import helios.data.component
import helios.flash
import helios.persist.component
from helios.persist.files import Files
from helios.routing import Router
import helios.session.component
import helios.views.component
from helios.wsgi import Application

from app.config import Config
from app.data import User, schema
from app.http import routes


class Application(Application):
	def __init__(self, config: Config):
		files = Files(config.persist)
		super().__init__(
			helios.app.Config(base_url=config.base_url),
			Router(routes),
			[
				helios.persist.component.Component(files),
				helios.session.component.Component(config.session, files),
				helios.data.component.Component(config.data, files, schema),
				helios.views.component.Component(config.views),
				helios.flash.Component(),
				helios.auth.Component(User),
			],
		)
