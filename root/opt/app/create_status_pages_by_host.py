#!/usr/bin/env python3

import os
import re
from collections import defaultdict

os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"

from uptime_kuma_api import UptimeKumaApi


KUMA_URL = "https://kuma.example.com"
KUMA_USERNAME = "cscd"
KUMA_PASSWORD = "<removed>"

DRY_RUN = False

MAIN_STATUS_PAGE_SLUG = "example"
MAIN_STATUS_PAGE_TITLE = "Example AG"


def parse_host_service(monitor_name):
    if " / " not in monitor_name:
        return None, None

    host, service = monitor_name.split(" / ", 1)
    return host.strip(), service.strip()


with UptimeKumaApi(KUMA_URL) as api:
    print("[+] Connected to Kuma")
    api.login(KUMA_USERNAME, KUMA_PASSWORD)
    print("[+] Login successful")

    monitors = api.get_monitors()
    status_pages = api.get_status_pages()

    existing_slugs = {page["slug"] for page in status_pages}

    monitors_by_host = defaultdict(list)

    for monitor in monitors:
        name = monitor.get("name", "")
        host, service = parse_host_service(name)

        if not host or not service:
            continue

        monitors_by_host[host].append({
            "id": monitor["id"],
            "name": name,
            "service": service,
            "type": monitor.get("type", "http"),
        })

    print(f"[+] Found {len(monitors_by_host)} hosts with monitors")

    public_group_list = []

    for weight, host in enumerate(sorted(monitors_by_host), start=1):
        host_monitors = sorted(
            monitors_by_host[host],
            key=lambda m: m["service"]
        )

        print()
        print(f"[+] Group: {host}")
        print(f"    Monitors: {len(host_monitors)}")

        for m in host_monitors:
            print(f"      - #{m['id']} {m['service']}")

        public_group_list.append({
            "name": host,
            "weight": weight,
            "monitorList": [
                {
                    "id": m["id"],
                    "name": m["service"],
                    "sendUrl": False,
                    "type": m["type"],
                }
                for m in host_monitors
            ],
        })

    if DRY_RUN:
        print()
        print("DRY_RUN=True, not changing Kuma")
        exit(0)

    if MAIN_STATUS_PAGE_SLUG not in existing_slugs:
        print()
        print(f"[+] Creating main status page: {MAIN_STATUS_PAGE_SLUG}")
        api.add_status_page(MAIN_STATUS_PAGE_SLUG, MAIN_STATUS_PAGE_TITLE)
    else:
        print()
        print(f"[+] Updating main status page: {MAIN_STATUS_PAGE_SLUG}")

    raw_page = api._call("getStatusPage", MAIN_STATUS_PAGE_SLUG)

    if "config" not in raw_page:
        raise RuntimeError(
            f"Unexpected getStatusPage response for {MAIN_STATUS_PAGE_SLUG}: {raw_page}"
        )

    config = raw_page["config"]

    config.update({
        "slug": MAIN_STATUS_PAGE_SLUG,
        "title": MAIN_STATUS_PAGE_TITLE,
        "description": "Example status grouped by host.",
        "icon": config.get("icon", "/icon.svg"),
        "theme": config.get("theme", "auto"),
        "autoRefreshInterval": config.get("autoRefreshInterval", 300),
        "published": True,
        "showTags": False,
        "domainNameList": config.get("domainNameList", []),
        "customCSS": config.get("customCSS"),
        "footerText": config.get("footerText"),
        "showPoweredBy": False,
        "analyticsId": config.get("analyticsId"),
        "analyticsScriptUrl": config.get("analyticsScriptUrl"),
        "analyticsType": config.get("analyticsType"),
        "showCertificateExpiry": False,
        "showOnlyLastHeartbeat": config.get("showOnlyLastHeartbeat", False),
        "rssTitle": config.get("rssTitle"),
    })

    if not config.get("analyticsType"):
        config["analyticsType"] = None
        config["analyticsId"] = None
        config["analyticsScriptUrl"] = None

    data = (
        MAIN_STATUS_PAGE_SLUG,
        config,
        "",
        public_group_list,
    )

    result = api._call("saveStatusPage", data)

    print()
    print("[+] Main status page saved")
    print(result)

print()
print("[+] Done")

