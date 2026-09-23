# 🚀 Networking & Infrastructure Services — Complete Week 1–4

This section documents the concepts and production-style work completed across the four-week Nginx networking project, including the integration between AWS ALB, Nginx, Flask, Redis, TLS, rate limiting, caching, security controls, and failure handling.

---

# 🟢 Week 1 — Nginx Reverse Proxy, Static Files & Traffic Control

## Objective

Build an Ubuntu EC2 application edge layer where Nginx is the public-facing HTTP server and Flask is isolated behind it.

## Architecture

```text
Internet
   |
   | HTTP :80
   v
Nginx
   |
   +---- Static files
   +---- Rate limiting
   +---- Gzip
   +---- Reverse proxy
             |
             v
       Flask :5007
       127.0.0.1
```

## Flask Backend Isolation

Flask was configured to bind only to localhost:

```python
app.run(host="127.0.0.1", port=5007)
```

Verify:

```bash
sudo ss -lntp | grep :5007
```

Expected:

```text
127.0.0.1:5007
```

## Nginx Reverse Proxy

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:5007/;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

The trailing slash on `proxy_pass` removes the `/api/` prefix:

```text
/api/users
    |
    v
/users
    |
    v
Flask
```

## Static Files

```nginx
root /var/www/html;
index index.html;

location /static/ {
    try_files $uri $uri/ =404;
}

location / {
    try_files $uri $uri/ =404;
}
```

Static requests are served directly by Nginx instead of reaching Flask.

## Gzip

```nginx
gzip on;
gzip_comp_level 5;
gzip_min_length 1000;

gzip_types
    text/plain
    text/css
    text/javascript
    application/javascript
    application/json
    application/xml
    image/svg+xml;
```

Responses below 1000 bytes are intentionally not compressed. A temporary >1 KB response was used to verify:

```text
Content-Encoding: gzip
```

## API Rate Limiting

The final API configuration:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=60r/m;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    limit_req_status 429;
}
```

A 100-request test produced:

```text
44 × 200
56 × 429
```

demonstrating Nginx request protection.

## Validation

```bash
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status nginx --no-pager
```

Logs:

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Week 1 Outcome

- Nginx reverse proxy
- Flask backend isolation
- Static file serving
- Proxy headers
- Gzip
- API rate limiting
- HTTP 429 handling
- Layer-by-layer troubleshooting

---

# 🔵 Week 2 — DNS, HTTPS, TLS, HTTP/2 & HSTS

## Objective

Secure the public connection and understand the TLS lifecycle.

## DNS

Dedicated hostname:

```text
nginx.mangomansions.in
```

The final architecture places AWS ALB in front of Nginx, so DNS resolves to the ALB.

## Let's Encrypt and Certbot

A Let's Encrypt certificate was obtained for:

```text
nginx.mangomansions.in
```

Certificate files were managed under:

```text
/etc/letsencrypt/live/nginx.mangomansions.in/
```

Important files:

```text
fullchain.pem
privkey.pem
```

Private keys must never be committed to GitHub.

## TLS

HTTPS is HTTP over TLS. TLS provides confidentiality, integrity, and server authentication.

### Final TLS Architecture

```text
Client
   |
   | HTTPS :443
   v
AWS ALB
   |
   | HTTP :80
   v
Nginx
   |
   v
Flask
```

Public TLS is terminated at the AWS ALB in the final architecture.

## HTTP → HTTPS Redirect

The ALB performs the public redirect:

```text
HTTP :80
   |
   v
ALB
   |
   | 301
   v
HTTPS :443
```

Verified:

```text
HTTP/1.1 301 Moved Permanently
Server: awselb/2.0
Location: https://nginx.mangomansions.in:443/health
```

## HTTP/2 and ALPN

The public endpoint returned:

```text
HTTP/2 200
```

ALPN (Application-Layer Protocol Negotiation) negotiates the application protocol during the TLS handshake, such as `h2` or `http/1.1`.

TLS provides the secure channel; ALPN negotiates the application protocol.

## TLS Version Verification

Public tests verified:

```text
TLS 1.1 → rejected
TLS 1.2 → accepted
TLS 1.3 → accepted
```

Because TLS terminates at the ALB, these public tests validate the ALB TLS policy rather than Nginx's local 443 listener.

## HSTS

```nginx
add_header Strict-Transport-Security "max-age=31536000" always;
```

Because public TLS terminates at the ALB and the ALB forwards HTTP to Nginx, the HSTS header was added to the ALB-facing Nginx `:80` server block.

Verified publicly:

```text
strict-transport-security: max-age=31536000
```

## OCSP Investigation

OCSP was investigated. No OCSP responder URI was found in the examined certificate and no explicit Nginx OCSP stapling configuration was present.

Therefore, OCSP stapling was investigated but was not claimed as configured.

## Week 2 Outcome

- DNS
- Let's Encrypt
- Certbot
- HTTPS
- TLS termination
- TLS 1.2 / 1.3
- TLS 1.1 rejection
- HTTP/2
- ALPN
- HSTS
- Certificate inspection
- OCSP investigation

---

# 🟣 Week 3 — Load Balancing, Redis, Caching & Sessions

## Objective

Move from one Flask process to a horizontally scaled application tier.

## Three Flask Instances

```text
Flask-1 → 127.0.0.1:5007
Flask-2 → 127.0.0.1:5008
Flask-3 → 127.0.0.1:5009
```

Each instance has a unique server ID.

## systemd

Each application runs as a service:

```text
flask-5007.service
flask-5008.service
flask-5009.service
```

Example:

```ini
[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/nginx-flask-reverse-proxy
Environment="PORT=5007"
Environment="SERVER_ID=flask-1"
ExecStart=/home/ubuntu/nginx-flask-reverse-proxy/app/venv/bin/python app/app.py
Restart=always
RestartSec=3
```

## Nginx Load Balancing

```nginx
upstream flask_backend {
    least_conn;
    server 127.0.0.1:5007;
    server 127.0.0.1:5008;
    server 127.0.0.1:5009;
}
```

`least_conn` chooses an upstream with the fewest active connections. It is not strict round-robin.

The `/api/whoami` endpoint verified traffic across all three instances.

## Redis Application Cache

The `/users` endpoint uses Redis with a 60-second TTL:

```python
cached_users = redis_client.get("users")

if cached_users:
    return cached_users, 200, {
        "Content-Type": "application/json",
        "X-Cache": "HIT"
    }

redis_client.setex("users", 60, response)
```

## Nginx Proxy Cache

```nginx
proxy_cache_path /var/cache/nginx/flask_cache
                 levels=1:2
                 keys_zone=flask_cache:10m
                 max_size=100m
                 inactive=60m
                 use_temp_path=off;
```

API cache:

```nginx
location /api/ {
    proxy_cache flask_cache;
    proxy_cache_valid 200 60s;

    add_header X-Proxy-Cache $upstream_cache_status always;

    proxy_pass http://flask_backend/;
}
```

Two distinct cache layers exist:

```text
Client
  |
  v
Nginx proxy_cache
  |
  | HIT → response immediately
  |
  | MISS
  v
Flask
  |
  v
Redis application cache
```

Headers:

```text
X-Proxy-Cache → Nginx cache
X-Cache        → Flask/Redis application cache
```

## Redis-Backed Sessions

```python
app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=False
)

app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30

Session(app)
```

A session created through one Flask instance was successfully read through another, proving that session state was shared through Redis.

```text
/api/session-test
       |
       v
Flask-1
       |
       v
Redis session

/api/session-get
       |
       v
Flask-2
       |
       v
Same session data
```

## Week 3 Outcome

- Three Flask instances
- systemd process management
- Nginx `least_conn`
- Redis
- Application caching
- Nginx proxy caching
- Shared Redis-backed sessions
- Horizontal scaling

---

# 🔴 Week 4 — Production-Style Capstone & High Availability

## Objective

Combine the previous weeks into a production-style networking architecture.

## Final Architecture

```text
                         Internet
                            |
                  nginx.mangomansions.in
                            |
                            v
                    AWS Application
                    Load Balancer
                       :443
                    TLS terminate
                            |
                     HTTP :80
                            |
                         Nginx
                 +----------+----------+
                 |          |          |
             rate limit   cache      gzip
                 |          |          |
                 +----------+----------+
                            |
                       least_conn
                    +-------+-------+
                    |       |       |
                  5007    5008    5009
                 Flask-1 Flask-2 Flask-3
                    \       |       /
                     \      |      /
                          Redis
                    /                          sessions             cache
```

## AWS ALB

The ALB became the public high-availability entry point.

Key behavior:

```text
Internet → ALB :443 → Nginx :80 → Flask
```

The ALB uses an ACM certificate for:

```text
nginx.mangomansions.in
```

## ALB Active Health Check

Target group health check:

```text
Protocol: HTTP
Port: 80
Path: /health
Expected status: 200
```

The ALB actively sends health-check requests and determines whether the EC2 target is healthy.

## Nginx Failure Detection

Nginx open-source in this project uses passive upstream failure detection. It does not have the same dedicated active health-check feature as Nginx Plus.

Therefore:

```text
ALB → active health check
Nginx → passive upstream failure detection
```

## UFW

UFW was configured with:

```text
Default incoming: deny
Default outgoing: allow
```

Allowed:

```text
22/tcp
80/tcp
```

Public 443 is not required at EC2 because the ALB terminates public HTTPS.

## AWS Security Groups

Layered path:

```text
Internet
   |
   v
ALB Security Group
   |
   v
EC2 Security Group
   |
   v
Nginx :80
   |
   v
Flask localhost ports
```

The EC2 security group restricts HTTP access to the ALB security group.

## Failure Test

Flask-5007 was intentionally stopped:

```bash
sudo systemctl stop flask-5007
```

Ten public requests were then sent through:

```text
https://nginx.mangomansions.in/api/whoami
```

All responses came from:

```text
flask-2 → 5008
flask-3 → 5009
```

No response came from Flask-5007.

The instance was restored:

```bash
sudo systemctl start flask-5007
```

Final state:

```text
flask-5007 → active
flask-5008 → active
flask-5009 → active
```

This demonstrated horizontal failure tolerance.

## Final Public Security Verification

Verified:

```text
HTTP → HTTPS              ✅
TLS 1.1 rejected         ✅
TLS 1.2 accepted         ✅
TLS 1.3 accepted         ✅
HTTP/2                    ✅
HSTS                      ✅
Rate limiting / 429      ✅
Gzip                      ✅
Proxy cache               ✅
Static files              ✅
3 Flask instances         ✅
Redis sessions            ✅
Redis application cache  ✅
ALB health check          ✅
Backend failure test      ✅
UFW default deny          ✅
```

## Week 4 Outcome

- AWS ALB
- ACM certificate
- TLS termination
- HTTP → HTTPS redirect
- HTTP/2
- HSTS
- UFW
- AWS Security Groups
- Nginx rate limiting
- Gzip
- Nginx proxy cache
- Redis
- Three Flask instances
- Load balancing
- Active ALB health checks
- Passive Nginx failure detection
- Failure testing
- Horizontal scaling

---

# 🧠 Final Networking Mental Model

```text
1. DNS
   |
   v
2. AWS ALB
   |
   | HTTPS :443
   | TLS termination
   | HTTP/2
   v
3. Nginx :80
   |
   +--> HSTS
   +--> Rate limiting
   +--> Gzip
   +--> Proxy cache
   +--> Static files
   |
   v
4. Nginx upstream
   |
   | least_conn
   +------> Flask-1 :5007
   +------> Flask-2 :5008
   +------> Flask-3 :5009
                |
                v
5. Redis
   |
   +--> Sessions
   +--> Application cache
```

## Failure Flow

```text
Flask-1 fails
     |
     v
Nginx/ALB failure handling
     |
     v
Traffic continues through:
     |
     +--> Flask-2
     +--> Flask-3
```

## Security Layers

```text
Internet
   |
   v
AWS ALB
   |
   +--> TLS
   +--> HTTP/2
   +--> HTTPS redirect
   |
   v
AWS Security Group
   |
   v
UFW
   |
   v
Nginx
   |
   +--> Rate limiting
   +--> HSTS
   +--> Reverse proxy isolation
   |
   v
Flask localhost
```

---

# 🎯 Interview-Ready Skills From This Project

You can now explain:

1. Why Nginx sits in front of Flask.
2. Why Flask binds to `127.0.0.1`.
3. How `proxy_pass` changes the request path.
4. How DNS maps the hostname to the infrastructure entry point.
5. What TLS provides.
6. What TLS termination means.
7. Why the ALB terminates public TLS in the final architecture.
8. What ALPN does.
9. How HTTP/2 is negotiated.
10. What HSTS does.
11. Why TLS 1.0/1.1 are rejected.
12. How Nginx performs reverse proxying.
13. How `least_conn` works.
14. Why three Flask instances provide horizontal scaling.
15. Why Redis is needed for shared sessions.
16. The difference between Redis application caching and Nginx proxy caching.
17. How rate limiting protects backend resources.
18. What HTTP 429 means.
19. Why gzip has a minimum response size.
20. How ALB active health checks work.
21. How Nginx passive failure detection differs from active health checks.
22. How UFW and AWS Security Groups form separate security layers.
23. How to troubleshoot a failed request layer by layer.
24. How to test a real backend failure.
25. Why the application can remain available when one Flask instance fails.

---

# 🏁 Networking & Infrastructure Services Completion

```text
Week 1 → Nginx Reverse Proxy             ✅
Week 2 → HTTPS / TLS / HTTP/2             ✅
Week 3 → Load Balancing / Redis / Cache   ✅
Week 4 → Production-Style Capstone       ✅
```

This README documents the completed Networking & Infrastructure Services project and the concepts actually implemented and verified during the four-week build.
