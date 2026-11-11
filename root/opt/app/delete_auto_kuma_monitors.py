#!/usr/bin/env python3

import os

os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"

from uptime_kuma_api import UptimeKumaApi

KUMA_URL = "https://kuma.example.com"
KUMA_USERNAME = "cscd"
KUMA_PASSWORD = "<removed>"

# Safety filter: only delete monitors whose URL points to the old wrong Flask URL
DELETE_URL_PREFIX = "http://kuma-python-flask/check/"

DRY_RUN = False

with UptimeKumaApi(KUMA_URL) as api:
    api.login(KUMA_USERNAME, KUMA_PASSWORD)

    monitors = api.get_monitors()

    targets = [
        m for m in monitors
        if m.get("url", "").startswith(DELETE_URL_PREFIX)
    ]

    print(f"Found {len(targets)} monitors to delete")

    for m in targets:
        print(f"- #{m['id']} {m['name']} -> {m.get('url')}")

    if DRY_RUN:
        print("\nDRY_RUN=True, nothing deleted.")
        print("Set DRY_RUN=False to actually delete.")
        exit(0)

    for m in targets:
        print(f"Deleting #{m['id']} {m['name']}")
        api.delete_monitor(m["id"])

    print("Done.")

