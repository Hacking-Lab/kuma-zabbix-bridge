#!/usr/bin/env python3

import configparser
import os
import re
import time
import fnmatch
from pathlib import Path

import requests
from flask import Flask, jsonify, request
from uptime_kuma_api import UptimeKumaApi, MonitorType


os.environ["REQUESTS_CA_BUNDLE"] = "/etc/ssl/certs/ca-certificates.crt"
os.environ["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"

CONFIG_FILE = Path(__file__).parent / "config.ini"

config = configparser.ConfigParser()

if not config.read(CONFIG_FILE):
    raise RuntimeError(f"Could not load config file: {CONFIG_FILE}")

ZABBIX_URL = config["zabbix"]["url"]
ZABBIX_TOKEN = config["zabbix"]["token"]
CACHE_TTL = int(config["zabbix"].get("cache_ttl_seconds", "3600"))
ZABBIX_CA_BUNDLE = config["zabbix"].get(
    "ca_bundle",
    "/etc/ssl/certs/ca-certificates.crt"
)

FLASK_HOST = config["flask"].get("host", "0.0.0.0")
FLASK_PORT = int(config["flask"].get("port", "8080"))
BASE_URL = config["flask"]["base_url"].rstrip("/")

KUMA_ENABLED = config["kuma"].getboolean("enabled", fallback=False)
KUMA_URL = config["kuma"].get("url", "").rstrip("/")
KUMA_USERNAME = config["kuma"].get("username", "")
KUMA_PASSWORD = config["kuma"].get("password", "")
KUMA_SYNC_TOKEN = config["kuma"].get("sync_token", "")
KUMA_INTERVAL = int(config["kuma"].get("monitor_interval", "60"))
KUMA_RETRY_INTERVAL = int(config["kuma"].get("monitor_retry_interval", "60"))
KUMA_MAX_RETRIES = int(config["kuma"].get("monitor_max_retries", "1"))
KUMA_DELETE_MISSING_DEFAULT = config["kuma"].getboolean(
    "delete_missing",
    fallback=False,
)

BRIDGE_URL_PREFIX = f"{BASE_URL}/check/"

SERVICE_WHITELIST = [
    s.strip().lower()
    for s in config["monitoring"].get("service_whitelist", "").splitlines()
    if s.strip()
]

HOST_DENYLIST = [
    s.strip().lower()
    for s in config["monitoring"].get("host_denylist", "").splitlines()
    if s.strip()
]

ONLY_PROBLEM_TRIGGERS = config["monitoring"].getboolean(
    "only_problem_triggers",
    fallback=True,
)


app = Flask(__name__)

TRIGGER_VALUE = {
    "0": "OK",
    "1": "PROBLEM",
}

TRIGGER_SEVERITY = {
    "0": "not_classified",
    "1": "information",
    "2": "warning",
    "3": "average",
    "4": "high",
    "5": "disaster",
}

cache = {
    "timestamp": 0,
    "triggers": [],
}


@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({
        "status": "NOK",
        "error": str(e),
    }), 500


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value


def zabbix_rpc(method, params):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": 1,
    }

    headers = {
        "Content-Type": "application/json-rpc",
        "Authorization": f"Bearer {ZABBIX_TOKEN}",
    }

    response = requests.post(
        ZABBIX_URL,
        headers=headers,
        json=payload,
        timeout=15,
        verify=ZABBIX_CA_BUNDLE,
    )
    response.raise_for_status()

    data = response.json()

    if "error" in data:
        raise RuntimeError(data["error"])

    return data["result"]


def get_triggers(force_refresh=False):
    now = time.time()

    if (
        not force_refresh
        and cache["triggers"]
        and now - cache["timestamp"] < CACHE_TTL
    ):
        return cache["triggers"]

    triggers = zabbix_rpc("trigger.get", {
        "output": [
            "triggerid",
            "description",
            "priority",
            "value",
            "lastchange",
            "status",
            "state",
        ],
        "selectHosts": ["hostid", "host", "name"],
        "expandDescription": True,
        "monitored": True,
        "active": True,
        "sortfield": "description",
    })

    cache["triggers"] = triggers
    cache["timestamp"] = now

    return triggers

def trigger_service_name(trigger):
    description = trigger.get("description", "")
    return slugify(description)

def service_allowed(service, description):
    if not SERVICE_WHITELIST:
        return True

    description = description.lower()

    for pattern in SERVICE_WHITELIST:
        if fnmatch.fnmatch(description, pattern):
            return True

    return False

def host_denied(host, zabbix_host="", hostid=""):
    haystack_values = [
        str(host).lower(),
        str(zabbix_host).lower(),
        str(hostid).lower(),
    ]

    for pattern in HOST_DENYLIST:
        for value in haystack_values:
            if fnmatch.fnmatch(value, pattern):
                return True

    return False



def build_monitor_name(host, service):
    return f"{host} / {service}"


def build_monitor_url(host, service):
    return f"{BASE_URL}/check/{host}/{service}"


def is_bridge_monitor(monitor):
    return monitor.get("url", "").startswith(BRIDGE_URL_PREFIX)


def discover_services(force_refresh=False):
    triggers = get_triggers(force_refresh=force_refresh)
    result = []

    for trigger in triggers:
        if not trigger.get("hosts"):
            continue

        host = trigger["hosts"][0]["name"]
        hostid = trigger["hosts"][0]["hostid"]
        zabbix_host = trigger["hosts"][0]["host"]

        if host_denied(host, zabbix_host, hostid):
            continue

        if ONLY_PROBLEM_TRIGGERS and trigger.get("value") != "1":
            continue

        description = trigger.get("description", "")
        service = trigger_service_name(trigger)

        if not service_allowed(service, description):
            continue

        value = trigger.get("value")
        priority = trigger.get("priority")

        result.append({
            "host": host,
            "zabbix_host": zabbix_host,
            "hostid": hostid,
            "service": service,
            "triggerid": trigger.get("triggerid"),
            "description": description,
            "priority": priority,
            "severity": TRIGGER_SEVERITY.get(priority, "unknown"),
            "value": value,
            "value_text": TRIGGER_VALUE.get(value, "unknown"),
            "status": "OK" if value == "0" else "NOK",
            "url": build_monitor_url(host, service),
        })

    return result


@app.get("/health")
def health():
    return jsonify({"status": "OK"}), 200


@app.get("/cache")
def cache_info():
    return jsonify({
        "cached_triggers": len(cache["triggers"]),
        "cache_timestamp": cache["timestamp"],
        "cache_ttl": CACHE_TTL,
    }), 200


@app.get("/services")
def services():
    return jsonify(discover_services()), 200

@app.get("/debug/triggers")
def debug_triggers():
    triggers = get_triggers(force_refresh=True)

    result = []

    for trigger in triggers:
        if not trigger.get("hosts"):
            continue

        host = trigger["hosts"][0]["name"]
        hostid = trigger["hosts"][0]["hostid"]
        zabbix_host = trigger["hosts"][0]["host"]

        description = trigger.get("description", "")
        service = trigger_service_name(trigger)

        denied = host_denied(host, zabbix_host, hostid)
        whitelisted = service_allowed(service, description)

        is_problem = trigger.get("value") == "1"
        problem_allowed = is_problem or not ONLY_PROBLEM_TRIGGERS
        
        allowed = (
            whitelisted
            and not denied
            and problem_allowed
        )

        result.append({
            "host": host,
            "zabbix_host": zabbix_host,
            "hostid": hostid,
            "description": description,
            "service": service,
            "whitelisted": whitelisted,
            "host_denied": denied,
            "allowed": allowed,
            "value": trigger.get("value"),
            "severity": TRIGGER_SEVERITY.get(trigger.get("priority"), "unknown"),
        })

    return jsonify(result), 200


@app.get("/check/<hostname>/<service>")
def check_service(hostname, service):
    triggers = get_triggers()
    service = service.lower().strip()

    matches = []

    for trigger in triggers:
        if not trigger.get("hosts"):
            continue

        host = trigger["hosts"][0]

        host_matches = (
            host["host"] == hostname
            or host["name"] == hostname
            or host["hostid"] == hostname
        )

        trigger_service = trigger_service_name(trigger)

        if host_matches and trigger_service == service:
            matches.append(trigger)

    if not matches:
        return jsonify({
            "status": "NOK",
            "host": hostname,
            "service": service,
            "error": "Trigger not found in Zabbix",
        }), 500

    problems = [
        trigger for trigger in matches
        if trigger.get("value") == "1"
    ]

    response = {
        "status": "OK" if not problems else "NOK",
        "host": matches[0]["hosts"][0]["name"],
        "zabbix_host": matches[0]["hosts"][0]["host"],
        "hostid": matches[0]["hosts"][0]["hostid"],
        "service": service,
        "matched_triggers": [
            {
                "triggerid": trigger.get("triggerid"),
                "description": trigger.get("description"),
                "priority": trigger.get("priority"),
                "severity": TRIGGER_SEVERITY.get(trigger.get("priority"), "unknown"),
                "value": trigger.get("value"),
                "value_text": TRIGGER_VALUE.get(trigger.get("value"), "unknown"),
                "lastchange": trigger.get("lastchange"),
            }
            for trigger in matches
        ],
    }

    return jsonify(response), 200 if not problems else 500


@app.get("/sync-kuma-preview")
@app.post("/sync-kuma-preview")
def sync_kuma_preview():
    token = request.args.get("token", "")

    if token != KUMA_SYNC_TOKEN:
        return jsonify({
            "status": "NOK",
            "error": "Unauthorized",
        }), 401

    if not KUMA_ENABLED:
        return jsonify({
            "status": "NOK",
            "error": "Kuma sync disabled in config.ini",
        }), 500

    discovered = discover_services(force_refresh=True)

    will_create = []
    already_exists = []
    will_delete = []

    discovered_names = {
        build_monitor_name(svc["host"], svc["service"])
        for svc in discovered
    }

    with UptimeKumaApi(KUMA_URL) as api:
        api.login(KUMA_USERNAME, KUMA_PASSWORD)

        kuma_monitors = api.get_monitors()
        existing_names = {m["name"] for m in kuma_monitors}

        for svc in discovered:
            name = build_monitor_name(svc["host"], svc["service"])
            url = build_monitor_url(svc["host"], svc["service"])

            item = {
                "name": name,
                "host": svc["host"],
                "service": svc["service"],
                "description": svc["description"],
                "url": url,
            }

            if name in existing_names:
                already_exists.append(item)
            else:
                will_create.append(item)

        for monitor in kuma_monitors:
            name = monitor.get("name")
            url = monitor.get("url", "")

            if not is_bridge_monitor(monitor):
                continue

            if name in discovered_names:
                continue

            will_delete.append({
                "id": monitor.get("id"),
                "name": name,
                "url": url,
            })

    return jsonify({
        "status": "OK",
        "discovered": len(discovered),
        "will_create_count": len(will_create),
        "already_exists_count": len(already_exists),
        "will_delete_count": len(will_delete),
        "will_create": will_create,
        "already_exists": already_exists,
        "will_delete": will_delete,
    }), 200


@app.post("/sync-kuma")
def sync_kuma():
    token = request.args.get("token", "")

    if token != KUMA_SYNC_TOKEN:
        return jsonify({
            "status": "NOK",
            "error": "Unauthorized",
        }), 401

    if not KUMA_ENABLED:
        return jsonify({
            "status": "NOK",
            "error": "Kuma sync disabled in config.ini",
        }), 500

    apply_changes = request.args.get("apply", "false").lower() == "true"

    delete_missing = (
        request.args.get("delete_missing", str(KUMA_DELETE_MISSING_DEFAULT))
        .lower() == "true"
    )

    discovered = discover_services(force_refresh=True)

    created = []
    existing = []
    failed = []
    deleted = []
    would_delete = []

    discovered_names = {
        build_monitor_name(svc["host"], svc["service"])
        for svc in discovered
    }

    with UptimeKumaApi(KUMA_URL) as api:
        api.login(KUMA_USERNAME, KUMA_PASSWORD)

        kuma_monitors = api.get_monitors()
        existing_names = {m["name"] for m in kuma_monitors}

        for svc in discovered:
            name = build_monitor_name(svc["host"], svc["service"])
            url = build_monitor_url(svc["host"], svc["service"])

            if name in existing_names:
                existing.append({
                    "name": name,
                    "url": url,
                })
                continue

            try:
                if apply_changes:
                    data = api._build_monitor_data(
                        type=MonitorType.HTTP,
                        name=name,
                        url=url,
                        method="GET",
                        interval=KUMA_INTERVAL,
                        retryInterval=KUMA_RETRY_INTERVAL,
                        maxretries=KUMA_MAX_RETRIES,
                        accepted_statuscodes=["200-299"],
                        timeout=48,
                        maxredirects=10,
                        ignoreTls=False,
                    )

                    data["conditions"] = []

                    result = api._call("add", data)
                else:
                    result = "DRY_RUN"

                created.append({
                    "name": name,
                    "url": url,
                    "result": result,
                })

            except Exception as e:
                failed.append({
                    "name": name,
                    "url": url,
                    "error": str(e),
                })

        for monitor in kuma_monitors:
            name = monitor.get("name")
            url = monitor.get("url", "")

            if not is_bridge_monitor(monitor):
                continue

            if name in discovered_names:
                continue

            item = {
                "id": monitor.get("id"),
                "name": name,
                "url": url,
            }

            if delete_missing and apply_changes:
                try:
                    api.delete_monitor(monitor["id"])
                    deleted.append(item)
                except Exception as e:
                    failed.append({
                        "name": name,
                        "url": url,
                        "error": str(e),
                    })
            else:
                would_delete.append(item)

    return jsonify({
        "status": "OK" if not failed else "NOK",
        "dry_run": not apply_changes,
        "delete_missing": delete_missing,
        "discovered": len(discovered),
        "created_count": len(created),
        "existing_count": len(existing),
        "failed_count": len(failed),
        "deleted_count": len(deleted),
        "would_delete_count": len(would_delete),
        "created": created,
        "existing": existing,
        "failed": failed,
        "deleted": deleted,
        "would_delete": would_delete,
    }), 200 if not failed else 500


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT)


