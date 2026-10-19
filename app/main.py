from helios.config import Environment

from app.config import ENV_FILE
from app.wsgi import Application

app = Application(Environment.load(env_file=ENV_FILE))
app.boot()
