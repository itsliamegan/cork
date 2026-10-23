def worker_exit(_server, worker):
	# Before closing the application, ensure that the worker actually has a loaded
	# one. If a worker failed to start, or if Gunicorn couldn't signal it, then it
	# has none.
	if hasattr(worker, "wsgi"):
		worker.wsgi.close()
