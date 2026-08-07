# Puter.js REST/HTTP API - Complete Reference

## Executive Summary

Puter's HTTP API uses **two parallel access patterns**:

1. **Driver RPC pattern** - ALL SDK methods (puter.ai.chat, puter.kv.set, etc.) go through a single endpoint: POST /drivers/call with the interface/driver/method specified in the JSON body.
2. **Direct REST endpoints** - Some features (filesystem, auth) also have dedicated REST routes.

Base URL: https://api.puter.com

---

## 1. Base URL and Authentication

### Base URL
- Production: https://api.puter.com
- Self-hosted: http://puter.localhost:4100
- Configurable in SDK: globalThis.PUTER_API_ORIGIN

### Auth Header
```
Authorization: Bearer <token>
```

### Token Types
- GUI token (type "gui") - issued during browser login, bound to origin
- Auth token (type "au") - standard API token

### Token Origin Binding
- Bound tokens: only replayed to the exact origin minted against
- Unbound/legacy: only honored against default API origin

### In Driver Calls: token sent in BOTH places
1. `Authorization: Bearer <token>` header
2. `auth_token: <token>` in JSON body

### Content-Type Quirk
Driver calls use: `text/plain;actually=json`
(Deliberately non-standard to bypass CORS preflight. Body is still JSON.)

---

## 2. Driver RPC Endpoint (Universal API Gateway)

```
POST https://api.puter.com/drivers/call
```

Request body:
```json
{
  "interface": "<interface-name>",
  "driver": "<driver-name-or-omit>",
  "method": "<method-name>",
  "args": { "...method arguments..." },
  "auth_token": "<your-token>",
  "test_mode": false
}
```

Success response:
```json
{
  "success": true,
  "result": { "..." },
  "service": { "name": "driver-name" }
}
```

Failure response:
```json
{
  "success": false,
  "error": { "..." }
}
```

Streaming: Content-Type `application/x-ndjson`, newline-delimited JSON

---

## 3. AI Chat

### Via Driver RPC (what the SDK uses)
```
POST https://api.puter.com/drivers/call
```
```json
{
  "interface": "puter-chat-completion",
  "driver": "ai-chat",
  "method": "complete",
  "args": {
    "messages": [
      {"role": "system", "content": "You are helpful"},
      {"role": "user", "content": "Hello!"}
    ],
    "model": "gpt-5-nano",
    "stream": false,
    "temperature": 0.7,
    "max_tokens": 1024
  },
  "auth_token": "<token>"
}
```

### Via Direct REST (OpenAI-compatible)
```
POST https://api.puter.com/puterai/openai/v1/chat/completions
Authorization: Bearer <token>
```
```json
{
  "model": "gpt-5-nano",
  "messages": [{"role": "user", "content": "Hello!"}],
  "stream": false
}
```

Other OpenAI-compatible:
- POST /puterai/openai/v1/completions
- POST /puterai/openai/v1/responses

Anthropic-compatible:
- POST /puterai/anthropic/v1/messages

### Model Listing (no auth required)
```
GET https://api.puter.com/puterai/chat/models
GET https://api.puter.com/puterai/chat/models/details
```

Response:
```json
[
  {
    "id": "gpt-5-nano",
    "provider": "openai",
    "name": "GPT-5 Nano",
    "context": 200000,
    "max_tokens": 64000,
    "cost": {
      "currency": "usd-cents",
      "tokens": 1000000,
      "input": 500,
      "output": 2500
    }
  }
]
```

---

## 4. Key-Value Store

### Via Driver RPC
Interface: `puter-kvstore`

| SDK Method | Driver Method | args |
|-----------|---------------|------|
| puter.kv.set(key, value) | set | {key, value, expireAt} |
| puter.kv.get(key) | get | {key} |
| puter.kv.incr(key) | incr | {key} |
| puter.kv.decr(key) | decr | {key} |
| puter.kv.del(key) | del | {key} |
| puter.kv.list() | list | {} |
| puter.kv.flush() | flush | {} |
| puter.kv.expire(key, ttl) | expire | {key, ttl} |
| puter.kv.expireAt(key, ts) | expireAt | {key, expireAt} |
| puter.kv.add(path, value) | add | {path, value} |
| puter.kv.remove(path, value) | remove | {path, value} |
| puter.kv.update(path, ops) | update | {path, operations} |

### curl: KV Set
```bash
curl -X POST https://api.puter.com/drivers/call \
  -H "Content-Type: text/plain;actually=json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"interface":"puter-kvstore","method":"set","args":{"key":"username","value":"alice"},"auth_token":"TOKEN"}'
```

### curl: KV Get
```bash
curl -X POST https://api.puter.com/drivers/call \
  -H "Content-Type: text/plain;actually=json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"interface":"puter-kvstore","method":"get","args":{"key":"username"},"auth_token":"TOKEN"}'
```

---

## 5. File System Endpoints

### Direct REST Routes
All require `Authorization: Bearer <token>` and subdomain `api`.

| SDK Method | HTTP | Path | Key Params |
|-----------|------|------|------------|
| puter.fs.write() | POST | /fs/write | {path, content} |
| puter.fs.read() | GET | /fs/read?file=<path> | Query: file |
| puter.fs.mkdir() | POST | /fs/mkdir | {path} |
| puter.fs.readdir() | GET/POST | /fs/readdir | {path} |
| puter.fs.stat() | POST | /fs/stat | {path} |
| puter.fs.delete() | POST | /fs/delete | {path, recursive} |
| puter.fs.rename() | POST | /fs/rename | {path, new_name} |
| puter.fs.copy() | POST | /fs/copy | {source, destination} |
| puter.fs.move() | POST | /fs/move | {source, destination} |
| puter.fs.touch() | POST | /fs/touch | {path} |
| puter.fs.search() | POST | /fs/search | {path, query} |

### Signed Upload Flow (large files)
1. POST /fs/startBatchWrite - get signed upload URLs
2. PUT <signed-url> - upload blob to storage
3. POST /fs/completeBatchWrite - finalize

### curl: Write
```bash
curl -X POST https://api.puter.com/fs/write \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path":"/hello.txt","content":"Hello, world!"}'
```

### curl: Read
```bash
curl -X GET "https://api.puter.com/fs/read?file=/hello.txt" \
  -H "Authorization: Bearer TOKEN"
```

---

## 6. Hosting Endpoints

| SDK Method | HTTP | Path | Key Params |
|-----------|------|------|------------|
| puter.hosting.create() | POST | /hosting/create | {subdomain, path} |
| puter.hosting.list() | POST | /hosting/list | {} |
| puter.hosting.delete() | POST | /hosting/delete | {subdomain} |
| puter.hosting.get() | POST | /hosting/get | {subdomain} |
| puter.hosting.update() | POST | /hosting/update | {subdomain, path} |

---

## 7. Auth Endpoints (Direct REST)

| Route | Method | Purpose |
|-------|--------|---------|
| /login | POST | Credential login |
| /login/otp | POST | OTP second factor |
| /signup | POST | Create account |
| /logout | POST | Clear session |
| /confirm-email | POST | Verify email |
| /send-pass-recovery-email | POST | Password reset |
| /set-pass-using-token | POST | Set new password |

---

## 8. Error Handling

### Retry behavior
- Retries on: 429, 502, 503, 504
- Backoff: [250, 500, 1000, 2000, 2000, 2000, 2000, 2000] ms (9 max)
- 401 triggers reauth then replay

### Common error codes
- reauth_required - token expired
- token_auth_failed - invalid token
- insufficient_funds / usage_limited - quota exceeded
- permission_denied - missing permission
- upstream_rate_limited - AI provider rate limit
- upstream_provider_unavailable - AI provider down
