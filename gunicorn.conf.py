def worker_exit(server, worker):
	# A worker only has an application once it has loaded one. The arbiter also
	# calls this hook with its own record of a worker that already died, which
	# never loaded one.
	if hasattr(worker, "wsgi"):
		worker.wsgi.close()
