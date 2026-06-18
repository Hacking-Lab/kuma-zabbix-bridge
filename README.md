# Kuma Zabbix Bridge
This software bridges Kuma to Zabbix

# Build
- edit config.ini in `./build/config/config.ini`
  - zabbix url and API key
  - kuma-zabbix-bridge API key
  - kuma username and password
- run `docker compose up -d --build`

# Example Setup
- Traefik + Kuma + Kuma-Zabbix-Bridge
  - zabbix url and API key
  - kuma-zabbix-bridge API key
  - kuma username and password
  - MariaDB username and password
- edit config.ini in `kuma-zabbix-bridge-setup-with-kuma-and-traefik/config`
- run `docker compose up -d`
- setup KUMA with username/password from config.ini


# Testing Kuma-Zabbix-Bridge
- assuming bridge has the IP 172.18.0.4 assigned

<img width="1264" height="823" alt="image" src="https://github.com/user-attachments/assets/9bc8fc3a-7f47-4e5d-8120-403c41eac279" />


## Simple
```bash
curl -s http://172.18.0.4:8080/health | jq
curl -s http://172.18.0.4:8080/services | jq
curl -s http://172.18.0.4:8080/cache | jq
```

<img width="845" height="322" alt="image" src="https://github.com/user-attachments/assets/9a098006-f8b0-46ab-a849-b69a8cc9b7ca" />


## Preview Monitor Creation
```bash
# find token in config.ini
curl -s -X POST "http://172.18.0.4:8080/sync-kuma-preview?token=<removed>" | jq
```

## Dry Run Monitor Creation
```bash
# find token in config.ini
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>" | jq
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>" | jq
```

## Create New Monitors
```bash
# find token in config.ini
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true" | jq
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true" | jq
```

## Create New Monitors and delete removed Zabbix Items
```bash
# find token in config.ini
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true&delete_missing=true" | jq
```

## Debugging Triggers
```bash
# find token in config.ini
curl -s http://172.18.0.4:8080/debug/triggers   | jq -r '.[] | select(.allowed==true) | .host' | sort -u
```


# Zabbix Debugging (without kuma-zabbix-bridge)
## appinfo.version
```bash
echo "==========================="
echo "apiinfo.version"
echo "==========================="

curl -s -X POST 'https://zabbix.example.com/api_jsonrpc.php'  -H 'Content-Type: application/json-rpc'  -d '{
   "jsonrpc": "2.0",
   "method": "apiinfo.version",
   "params": {},
   "id": 1
 }' | jq
```

## host.get
```bash
echo "==========================="
echo "host.get"
echo "==========================="

curl -s \
  -X POST \
  -H "Content-Type: application/json-rpc" \
  -H "Authorization: Bearer <removed>" -d '{
    "jsonrpc": "2.0",
    "method": "host.get",
    "params": {
      "output": ["host", "name", "status"]
    },
    "id": 1
  }' \
  https://zabbix.example.com/api_jsonrpc.php | jq
```

## service.get
```bash
echo "==========================="
echo "service.get"
echo "==========================="

curl -s -X POST 'https://zabbix.example.com/api_jsonrpc.php'   -H 'Content-Type: application/json-rpc'   -H 'Authorization: Bearer <removed>'   -d '{
    "jsonrpc": "2.0",
    "method": "service.get",
    "params": {
      "output": ["name", "status"]
    },
    "id": 1
  }' | jq
```

## item.get
```bash
echo "==========================="
echo "item.get"
echo "==========================="
curl -s -X POST 'https://zabbix.example.com/api_jsonrpc.php'   -H 'Content-Type: application/json-rpc'   -H 'Authorization: Bearer <removed>'   -d '{
    "jsonrpc": "2.0",
    "method": "item.get",
    "params": {
      "output": ["name", "hostid", "status"]
    },
    "id": 1
  }' | jq
```

## trigger.get
```bash
echo "==========================="
echo "trigger.get"
echo "==========================="
curl -s -X POST -H "Content-Type: application/json-rpc" -H "Authorization: Bearer <removed>" -d '{
    "jsonrpc": "2.0",
    "method": "trigger.get",
    "params": {
      "output": [
        "description",
        "priority",
        "value",
        "lastchange"
      ],
      "selectHosts": ["host"],
      "filter": {
        "value": 1
      },
      "monitored": true,
      "active": true
    },
    "id": 1
  }' \
  https://zabbix.example.com/api_jsonrpc.php | jq
```



