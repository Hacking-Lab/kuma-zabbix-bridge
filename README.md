# Kuma Zabbix Bridge
This software bridges Kuma to Zabbix

# Kuma
## Simple
```bash
curl -s http://172.18.0.4:8080/health | jq
curl -s http://172.18.0.4:8080/services | jq
curl -s http://172.18.0.4:8080/cache | jq
```

## Preview Monitor Creation
```bash
curl -s -X POST "http://172.18.0.4:8080/sync-kuma-preview?token=<removed>" | jq
```

## Dry Run Monitor Creation
```bash
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>" | jq
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>" | jq
```

## Create New Monitors
```bash
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true" | jq
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true" | jq
```

## Create New Monitors and delete removed Zabbix Items
```bash
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true&delete_missing=true" | jq
```

## Debugging Triggers
```bash
curl -s http://172.18.0.4:8080/debug/triggers   | jq -r '.[] | select(.allowed==true) | .host' | sort -u
```


# ALL
```bash
curl -s http://172.18.0.4:8080/health | jq
curl -s http://172.18.0.4:8080/services | jq
curl -s http://172.18.0.4:8080/cache | jq

curl -s -X POST "http://172.18.0.4:8080/sync-kuma-preview?token=<removed>" | jq
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>" | jq
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true" | jq
curl -s -X POST "http://172.18.0.4:8080/sync-kuma?token=<removed>&apply=true&delete_missing=true" | jq
```


# Zabbix
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



