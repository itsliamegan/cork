import helios.auth
from helios.config import Environment
import helios.database
import helios.flash
import helios.form
import helios.limit
from helios.routing import Router
import helios.session
import helios.view.provider
from helios.wsgi import Application

from app import User, config, models
from app.http import routes
from app.views import components, helpers


class Application(Application):
	def __init__(self, environment: Environment):
		super().__init__(
			config.application(environment),
			Router(routes),
			[
				helios.view.provider.Provider(
					config.views(environment),
					helpers=helpers,
					components=components,
				),
				helios.session.Provider(
					config.session(environment),
					config.session_driver(environment),
				),
				helios.database.Provider(config.database(environment), models),
				helios.flash.Provider(),
				helios.form.Provider(),
				helios.auth.Provider(User),
			],
			[helios.limit.Middleware(config.rate_limit(environment))],
		)
