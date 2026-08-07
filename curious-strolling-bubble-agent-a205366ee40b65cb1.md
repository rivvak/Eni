# Puter KV Store REST API — Exact Endpoints

## Root Cause of "Driver not found"

The user was using `interface: "puter-kv"` — **WRONG**. The correct interface name is **`puter-kvstore`**.

The JS SDK (`puter.kv.set()`, etc.) internally calls `utils.makeDriverMethod({ iface: 'puter-kvstore', method: 'set', ... })` which routes through `POST /drivers/call`.

## Confirmed Architecture

All KV operations go through the **single endpoint**: `POST https://api.puter.com/drivers/call`

The `DriverController` resolves the interface name → finds the `KVStoreDriver` (registered with `driverInterface = 'puter-kvstore'`) → dispatches the method.

## Exact HTTP Request Format

### Common Structure

```
POST https://api.puter.com/drivers/call
Content-Type: text/plain;actually=json
Authorization: Bearer <your-puter-token>
```

Body (JSON):
```json
{
  "interface": "puter-kvstore",
  "method": "<method>",
  "args": { ... }
}
```

The `auth_token` field can also be passed in the body (SDK does both header + body), but the `Authorization: Bearer` header is the primary auth mechanism.

---

### 1. SET

```json
{
  "interface": "puter-kvstore",
  "method": "set",
  "args": {
    "key": "mykey",
    "value": "myvalue",
    "expireAt": null
  }
}
```

- `key` (string, required) — max 1KB
- `value` (any JSON-serializable, required) — max 400KB
- `expireAt` (number, optional) — Unix timestamp for TTL expiration

Response: `{ "success": true, "result": true }`

### 2. GET

```json
{
  "interface": "puter-kvstore",
  "method": "get",
  "args": {
    "key": "mykey"
  }
}
```

- `key` (string or string[], required) — single key returns single value; array of keys returns array of values

Response: `{ "success": true, "result": "<value or null>" }`

### 3. DEL

```json
{
  "interface": "puter-kvstore",
  "method": "del",
  "args": {
    "key": "mykey"
  }
}
```

- `key` (string, required)

Response: `{ "success": true, "result": true }`

### 4. LIST

```json
{
  "interface": "puter-kvstore",
  "method": "list",
  "args": {
    "as": "keys",
    "pattern": "prefix:*",
    "limit": 100,
    "cursor": null,
    "offset": null,
    "includeTotal": false,
    "fetchUntilFull": false
  }
}
```

- `as` (string, optional) — `"keys"` | `"values"` | `"entries"` (default: entries)
- `pattern` (string, optional) — wildcard prefix filter (e.g. `"fruit:*"`)
- `limit` (number, optional) — page size
- `cursor` (string, optional) — pagination cursor from previous page
- `includeTotal` (boolean, optional) — return total count (metered!)
- `fetchUntilFull` (boolean, optional) — keep fetching until page is full

Response: `{ "success": true, "result": [ ... ] }` or paginated envelope with cursor

### 5. BATCH PUT

```json
{
  "interface": "puter-kvstore",
  "method": "batchPut",
  "args": {
    "items": [
      { "key": "k1", "value": "v1", "expireAt": null },
      { "key": "k2", "value": "v2" }
    ]
  }
}
```

### 6. FLUSH (clear all)

```json
{
  "interface": "puter-kvstore",
  "method": "flush",
  "args": {}
}
```

### 7. INCR

```json
{
  "interface": "puter-kvstore",
  "method": "incr",
  "args": {
    "key": "counter",
    "pathAndAmountMap": { ".": 1 }
  }
}
```

### 8. DECR

```json
{
  "interface": "puter-kvstore",
  "method": "decr",
  "args": {
    "key": "counter",
    "pathAndAmountMap": { ".": 1 }
  }
}
```

### 9. EXPIRE

```json
{
  "interface": "puter-kvstore",
  "method": "expire",
  "args": {
    "key": "mykey",
    "ttl": 3600
  }
}
```

### 10. EXPIRE AT

```json
{
  "interface": "puter-kvstore",
  "method": "expireAt",
  "args": {
    "key": "mykey",
    "timestamp": 1700000000
  }
}
```

### 11. UPDATE

```json
{
  "interface": "puter-kvstore",
  "method": "update",
  "args": {
    "key": "mykey",
    "pathAndValueMap": { "field.subfield": "newvalue" },
    "ttl": null
  }
}
```

### 12. ADD (append to list)

```json
{
  "interface": "puter-kvstore",
  "method": "add",
  "args": {
    "key": "mylist",
    "pathAndValueMap": { ".": "item1" }
  }
}
```

### 13. REMOVE (remove path)

```json
{
  "interface": "puter-kvstore",
  "method": "remove",
  "args": {
    "key": "mykey",
    "paths": ["field.subfield"]
  }
}
```

## Rate Limits

- Default: 400 requests per 10 seconds
- Free tier: 400/10s
- Temp user: 200/10s

## Source Files Confirmed

- Backend driver: `src/backend/drivers/kv/KVStoreDriver.ts` — `driverInterface = 'puter-kvstore'`
- SDK module: `src/puter-js/src/modules/kv/*.js` — `iface: 'puter-kvstore'`
- SDK network: `src/puter-js/src/lib/networkUtils.js` — `POST /drivers/call`, `Content-Type: text/plain;actually=json`
- Controller: `src/backend/controllers/drivers/DriverController.ts` — parses `{interface, method, driver, args}` from body

## Minimal curl Examples

### Set a key:
```bash
curl -X POST https://api.puter.com/drivers/call \
  -H "Content-Type: text/plain;actually=json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"interface":"puter-kvstore","method":"set","args":{"key":"hello","value":"world"}}'
```

### Get a key:
```bash
curl -X POST https://api.puter.com/drivers/call \
  -H "Content-Type: text/plain;actually=json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"interface":"puter-kvstore","method":"get","args":{"key":"hello"}}'
```

### Delete a key:
```bash
curl -X POST https://api.puter.com/drivers/call \
  -H "Content-Type: text/plain;actually=json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"interface":"puter-kvstore","method":"del","args":{"key":"hello"}}'
```

### List keys:
```bash
curl -X POST https://api.puter.com/drivers/call \
  -H "Content-Type: text/plain;actually=json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"interface":"puter-kvstore","method":"list","args":{"as":"keys"}}'
```
