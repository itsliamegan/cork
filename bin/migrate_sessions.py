#!/usr/bin/env python

import json
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "data/sessions.json"

with open(path) as f:
	data = json.load(f)

for id, session in data.items():
	if "items" not in session:
		data[id] = {"items": session, "last_active_at": None}

with open(path, "w") as f:
	json.dump(data, f)

print(f"Migrated {len(data)} sessions in {path}")
