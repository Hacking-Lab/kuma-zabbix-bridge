#!/usr/bin/env python3

import os
import yaml
from collections import defaultdict
from uptime_kuma_api import UptimeKumaApi

os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"

KUMA_URL = "https://kuma.example.com"
KUMA_USERNAME = "cscd"
KUMA_PASSWORD = "<removed>

MAIN_STATUS_PAGE_SLUG = "example"
MAIN_STATUS_PAGE_TITLE = "Example AG"

OUTPUT_FILE = "kuma-status-pages.yml"

def parse_host_service(monitor_name):
    if " / " not in monitor_name:
        return None, None

    host, service = monitor_name.split(" / ", 1)
    return host.strip(), service.strip()


def to_plain(value):
    """
    Convert Enum values and other non-YAML-friendly
    objects into plain Python types.
    """
    if hasattr(value, "value"):
        return value.value

    return value


with UptimeKumaApi(KUMA_URL, timeout=60) as api:
    print("[+] Connected to Kuma")

    api.login(KUMA_USERNAME, KUMA_PASSWORD)

    print("[+] Login successful")

    monitors = api.get_monitors()

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
            "type": to_plain(monitor.get("type", "http")),
        })

    print(f"[+] Found {len(monitors_by_host)} hosts with monitors")

    config = {
        "version": 1,
        "defaults": {
            "strict_monitor_matching": True,
            "show_powered_by": False,
            "send_url": False,
        },
        "status_pages": [
            {
                "name": MAIN_STATUS_PAGE_TITLE,
                "slug": MAIN_STATUS_PAGE_SLUG,
                "title": MAIN_STATUS_PAGE_TITLE,
                "description": "Example by Host",
                "theme": "auto",
                "published": True,
                "show_tags": False,
                "show_powered_by": False,
                "show_certificate_expiry": False,
                "groups": [],
            }
        ],
    }

    page = config["status_pages"][0]

    for weight, host in enumerate(sorted(monitors_by_host), start=1):

        host_monitors = sorted(
            monitors_by_host[host],
            key=lambda m: m["service"]
        )

        group = {
            "name": host,
            "weight": weight,
            "monitors": [],
        }

        for m in host_monitors:
            group["monitors"].append({
                "id": m["id"],
                "name": m["name"],
                "display_name": m["service"],
                "service": m["service"],
                "type": to_plain(m["type"]),
                "send_url": False,
            })

        page["groups"].append(group)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        yaml.safe_dump(
            config,
            f,
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        )

    print(f"[+] Exported config to {OUTPUT_FILE}")

print("[+] Done")
