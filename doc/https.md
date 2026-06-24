# HTTPS / TLS Setup

**LM-Proxy** can serve the OpenAI-compatible API directly over HTTPS by terminating TLS
itself (via the underlying Uvicorn server), or you can keep it on plain HTTP and put a
reverse proxy in front. This guide covers both approaches.

---

## Built-in TLS Termination

LM-Proxy exposes two configuration options that are passed straight through to Uvicorn:

| Option         | Description                                  |
| -------------- | -------------------------------------------- |
| `ssl_keyfile`  | Path to the private key file (PEM).          |
| `ssl_certfile` | Path to the certificate file (PEM).          |

When **both** are set, the server starts on `https://`. If either is `None` (the default),
plain HTTP is used.

**Configuration:**
```yaml
host: "0.0.0.0"
port: 8443
ssl_keyfile: "/etc/lm-proxy/tls/privkey.pem"
ssl_certfile: "/etc/lm-proxy/tls/fullchain.pem"

connections:
  openai:
    api_type: "openai"
    api_key: "env:OPENAI_API_KEY"

routing:
  "*": "openai.*"
```

Keep secrets out of the config file by referencing environment variables with the
`env:VAR_NAME` syntax (resolved at load time). Paths can also be supplied this way:

```yaml
ssl_keyfile: "env:LM_PROXY_SSL_KEYFILE"
ssl_certfile: "env:LM_PROXY_SSL_CERTFILE"
```

Start the server as usual:
```bash
lm-proxy --config config.yaml
```

The client then targets the HTTPS endpoint:
```bash
curl https://your-host:8443/v1/chat/completions \
  -H "Authorization: Bearer YOUR_VIRTUAL_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "gpt-5", "messages": [{"role": "user", "content": "Hello"}]}'
```

---

## Obtaining Certificates

### Production — Let's Encrypt

Use [certbot](https://certbot.eff.org/) to issue a free, trusted certificate:
```bash
certbot certonly --standalone -d proxy.example.com
```

The resulting files live under `/etc/letsencrypt/live/proxy.example.com/`:
- `privkey.pem`  → `ssl_keyfile`
- `fullchain.pem` → `ssl_certfile`

Certificates expire every 90 days; certbot's renewal timer handles this. Restart (or
reload) LM-Proxy after each renewal so the new certificate is picked up — e.g. via a
certbot `--deploy-hook`.

### Development — Self-Signed

For local testing, generate a self-signed certificate with OpenSSL:
```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout privkey.pem -out fullchain.pem \
  -days 365 -subj "/CN=localhost"
```

Clients must skip verification for self-signed certs (e.g. `curl -k`, or
`httpx.Client(verify=False)`). **Never** disable verification in production.

---

## HTTPS When Accessing by IP Address (No Domain)

If you reach the proxy at `https://203.0.113.10:8443` and have **no domain name**, you
cannot use Let's Encrypt — public CAs only issue certificates for domain names, never bare
IPs. Your only option is a certificate you generate yourself, with the IP embedded in its
**Subject Alternative Name (SAN)**, that clients are told to trust.

Two things make this work, and both are mandatory:
1. The IP must appear as an `IP:` entry in the certificate's SAN. Modern clients ignore the
   old Common Name (`CN`) field, so a cert without the SAN entry fails verification even if
   the IP looks correct.
2. Because the certificate is self-signed, each client must explicitly trust it (or its CA)
   — otherwise it is rejected as untrusted.

Follow the steps below.

### Step 1 — Generate a certificate with the IP in the SAN

Replace `203.0.113.10` with your server's IP:
```bash
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout privkey.pem -out fullchain.pem \
  -days 365 \
  -subj "/CN=203.0.113.10" \
  -addext "subjectAltName=IP:203.0.113.10"
```

To allow several access points (e.g. public IP, loopback, and `localhost`), list them all:
```bash
  -addext "subjectAltName=IP:203.0.113.10,IP:127.0.0.1,DNS:localhost"
```

> Whatever string the client dials must be in the SAN. A cert listing only `127.0.0.1`
> will **fail** when a remote client connects to the public IP.

### Step 2 — Point LM-Proxy at the certificate

```yaml
host: "0.0.0.0"
port: 8443
ssl_keyfile: "privkey.pem"
ssl_certfile: "fullchain.pem"

connections:
  openai:
    api_type: "openai"
    api_key: "env:OPENAI_API_KEY"

routing:
  "*": "openai.*"
```

Start the server: `lm-proxy --config config.yaml`. It now serves HTTPS on the IP.

### Step 3 — Trust the certificate on each client

The proxy is fully working at this point — but because the certificate is self-signed,
clients reject it until told to trust it. Pick one:

- **Quick test (skip verification):** `curl -k https://203.0.113.10:8443/v1/...`, or in
  Python `httpx.Client(verify=False)`. Convenient, but offers no protection against
  man-in-the-middle — use only for throwaway testing.
- **Trust the specific certificate (recommended):** distribute `fullchain.pem` to clients
  and point them at it. This keeps verification on:
  ```bash
  curl --cacert fullchain.pem https://203.0.113.10:8443/v1/chat/completions \
    -H "Authorization: Bearer YOUR_VIRTUAL_KEY" \
    -H "Content-Type: application/json" \
    -d '{"model": "gpt-5", "messages": [{"role": "user", "content": "Hello"}]}'
  ```
  ```python
  import httpx
  client = httpx.Client(base_url="https://203.0.113.10:8443", verify="fullchain.pem")
  ```
  The OpenAI Python SDK accepts a custom `http_client`, so you can pass the same verified
  `httpx.Client` to it.
- **Trust system-wide:** install `fullchain.pem` into the OS trust store (e.g.
  `/usr/local/share/ca-certificates/` + `update-ca-certificates` on Debian/Ubuntu) so all
  tools on that host trust it without per-call flags.

> **Tip:** If you control more than one machine, generating a small internal CA once and
> issuing IP certs from it scales better than copying a self-signed cert everywhere — you
> distribute the CA root a single time, then reissue server certs freely.

---

## Alternative: TLS at a Reverse Proxy

In many deployments it is preferable to terminate TLS at a dedicated reverse proxy
(nginx, Caddy, Traefik, or a cloud load balancer) and let LM-Proxy listen on plain HTTP
on a private network. This centralizes certificate management and offloads TLS from the
application.

In this setup, **leave `ssl_keyfile` / `ssl_certfile` unset** and run LM-Proxy on HTTP:
```yaml
host: "127.0.0.1"
port: 8000
```

**nginx example:**
```nginx
server {
    listen 443 ssl;
    server_name proxy.example.com;

    ssl_certificate     /etc/letsencrypt/live/proxy.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/proxy.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Required for streaming (SSE) responses
        proxy_buffering off;
        proxy_read_timeout 300s;
    }
}
```

> **Streaming note:** `/v1/chat/completions` with `"stream": true` returns a
> `text/event-stream`. Disable response buffering (`proxy_buffering off` in nginx) so
> tokens are flushed to the client as they arrive.

**Caddy example** (automatic certificates):
```caddy
proxy.example.com {
    reverse_proxy 127.0.0.1:8000 {
        flush_interval -1
    }
}
```

---

## Choosing an Approach

| Scenario                                   | Recommended                          |
| ------------------------------------------ | ------------------------------------ |
| Single instance, simple deployment         | Built-in TLS termination             |
| Multiple instances / load balancing        | Reverse proxy or load balancer       |
| Automatic certificate renewal preferred    | Caddy / cloud load balancer          |
| Local development & testing                | Built-in TLS with self-signed cert   |

---

## See Also

- [HTTP Header Management](./http_headers.md)
- [Uvicorn — HTTPS deployment](https://www.uvicorn.org/deployment/#running-with-https)
- [certbot Documentation](https://certbot.eff.org/)
