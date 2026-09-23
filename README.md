# 🚀 Nginx Flask Reverse Proxy

Networking & Infrastructure Services

A production-style DevOps project that demonstrates how to deploy a **Flask application behind Nginx** on an **Ubuntu AWS EC2 instance**.

The project focuses on the fundamentals of an application edge layer:

- Nginx reverse proxy
- Flask backend
- Static file serving
- Proxy headers
- Gzip compression
- API rate limiting
- HTTP `429 Too Many Requests`
- Nginx access/error logs
- Backend isolation using `127.0.0.1`
- Route and configuration testing

> **Project:** `nginx-flask-reverse-proxy`  
> **Phase:** Networking & Infrastructure Services — Week 1

---

## 📌 Project Overview

The goal of this project is to place Nginx in front of a Flask application and make Nginx responsible for handling incoming HTTP traffic.

Instead of exposing Flask directly to clients:

```text
Client
  |
  v
Flask :5007
```

the architecture uses Nginx as the public entry point:

```text
Client
   |
   | HTTP :80
   v
+-------------------+
|       Nginx       |
|                   |
| Static Files      |
| Reverse Proxy     |
| Gzip              |
| Rate Limiting     |
+---------+---------+
          |
          | 127.0.0.1:5007
          v
+-------------------+
|       Flask       |
|      :5007        |
+-------------------+
```

This separation is important because Nginx can handle traffic-management responsibilities before requests reach the application.

---

# 🏗️ Architecture

## Request Flow

### Static Content

```text
Browser
   |
   | GET /
   v
Nginx :80
   |
   v
/var/www/html/index.html
```

### Static Directory

```text
Browser
   |
   | GET /static/index.html
   v
Nginx :80
   |
   v
/var/www/html/static/index.html
```

### API Request

```text
Client
   |
   | GET /api/users
   v
Nginx :80
   |
   | proxy_pass
   v
Flask 127.0.0.1:5007
   |
   v
/ users
```

### Rate-Limited Request

```text
Client
   |
   | High request rate
   v
Nginx
   |
   +---- Allowed ----> Flask
   |
   +---- Excess -----> HTTP 429
```

---

# 🧰 Technologies Used

| Technology | Purpose |
|---|---|
| Ubuntu | Linux server |
| AWS EC2 | Cloud compute instance |
| Nginx | Web server and reverse proxy |
| Python | Application runtime |
| Flask | Backend web application |
| Bash | Server/testing automation |
| curl | HTTP testing |
| Git/GitHub | Source control and project documentation |

---

# 📁 Project Structure

```text
nginx-flask-reverse-proxy/
│
├── app/
│   ├── app.py
│   └── requirements.txt
│
├── nginx/
│   └── nginx.conf
│
├── scripts/
│   └── setup.sh
│
├── static/
│   └── index.html
│
├── tests/
│   └── test_routes.sh
│
├── .gitignore
└── README.md
```

---

# 🐍 Flask Application

The Flask application runs on:

```text
127.0.0.1:5007
```

The application is intentionally bound to localhost:

```python
app.run(
    host="127.0.0.1",
    port=5007
)
```

This means Flask is not intended to be directly exposed to external clients.

## Application Routes

### `GET /`

Returns:

```text
Flask application is running
```

### `GET /users`

Returns a JSON list of users:

```json
{
  "users": [
    {
      "id": 1,
      "name": "Ayush"
    },
    {
      "id": 2,
      "name": "DevOps"
    },
    {
      "id": 3,
      "name": "Engineer"
    }
  ]
}
```

### `GET /health`

Returns:

```json
{
  "status": "healthy"
}
```

---

# 🌐 Nginx Configuration

Nginx listens publicly on:

```text
0.0.0.0:80
```

Flask listens locally on:

```text
127.0.0.1:5007
```

The API location uses:

```nginx
location /api/ {

    limit_req zone=api_limit;
    limit_req_status 429;

    proxy_pass http://127.0.0.1:5007/;

    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

The trailing slash in:

```nginx
proxy_pass http://127.0.0.1:5007/;
```

means that the `/api/` prefix is removed before the request is forwarded.

For example:

```text
/api/users
```

becomes:

```text
/users
```

when it reaches Flask.

---

# 📂 Static File Serving

Nginx serves static files directly from:

```text
/var/www/html
```

Configuration:

```nginx
location /static/ {
    try_files $uri $uri/ =404;
}
```

This prevents static-file requests from unnecessarily reaching Flask.

Example:

```text
/static/index.html
        |
        v
Nginx
        |
        v
/var/www/html/static/index.html
```

---

# 📦 Gzip Compression

Gzip compression is enabled to reduce the size of suitable HTTP responses.

Configuration:

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

### Why?

Smaller responses can reduce bandwidth usage and improve transfer time, especially for larger text-based responses.

### Test

A response larger than the configured minimum can be tested with:

```bash
curl -H "Accept-Encoding: gzip" -I http://127.0.0.1/test.txt
```

Expected header:

```text
Content-Encoding: gzip
```

---

# 🚦 API Rate Limiting

The API is protected with Nginx request rate limiting.

The shared rate-limit zone is configured inside the Nginx `http` context:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

The API uses the zone:

```nginx
location /api/ {
    limit_req zone=api_limit;
    limit_req_status 429;

    proxy_pass http://127.0.0.1:5007/;
}
```

### Configuration Meaning

```text
rate=10r/s
```

means approximately **10 requests per second per client IP**.

```text
$binary_remote_addr
```

is used to identify clients by their IP address.

Requests that exceed the configured limit can receive:

```text
HTTP 429 Too Many Requests
```

### Test

Run:

```bash
for i in {1..30}; do
    curl -s -o /dev/null -w "%{http_code}\n" \
    http://127.0.0.1/api/health
done
```

A rapid burst should produce a mixture containing:

```text
200
429
429
429
...
```

The exact pattern can vary because Nginx's request-rate algorithm controls when requests are accepted or rejected.

---

# 🔐 Proxy Headers

Nginx forwards useful information about the original request to Flask:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

These headers allow the backend to receive information such as:

- Original `Host`
- Client IP
- Proxy chain
- Original HTTP/HTTPS scheme

This becomes especially important when applications are deployed behind multiple reverse proxies or load balancers.

---

# 🧪 Testing

## 1. Test Nginx Homepage

```bash
curl -i http://127.0.0.1/
```

Expected:

```text
HTTP/1.1 200 OK
```

---

## 2. Test Static Content

```bash
curl -i http://127.0.0.1/static/index.html
```

Expected:

```text
HTTP/1.1 200 OK
```

---

## 3. Test Users API

```bash
curl -i http://127.0.0.1/api/users
```

Expected:

```text
HTTP/1.1 200 OK
```

Response:

```json
{
  "users": [
    {"id": 1, "name": "Ayush"},
    {"id": 2, "name": "DevOps"},
    {"id": 3, "name": "Engineer"}
  ]
}
```

---

## 4. Test Health API

```bash
curl -i http://127.0.0.1/api/health
```

Expected:

```text
HTTP/1.1 200 OK
```

Response:

```json
{
  "status": "healthy"
}
```

---

## 5. Test Rate Limiting

```bash
for i in {1..30}; do
    curl -s -o /dev/null -w "%{http_code}\n" \
    http://127.0.0.1/api/health
done
```

Expected to see `429` responses when requests exceed the configured rate.

---

# 🔍 Verify Backend Binding

Check which address Flask is listening on:

```bash
sudo ss -lntp | grep :5007
```

Expected:

```text
127.0.0.1:5007
```

The application should not be exposed as:

```text
0.0.0.0:5007
```

The intended traffic path is:

```text
Client → Nginx → Flask
```

rather than:

```text
Client → Flask
```

---

# ⚙️ Nginx Validation

Always validate the configuration before reloading Nginx:

```bash
sudo nginx -t
```

Expected:

```text
syntax is ok
test is successful
```

Reload:

```bash
sudo systemctl reload nginx
```

Check service status:

```bash
sudo systemctl status nginx --no-pager
```

Expected:

```text
Active: active (running)
```

---

# 📜 Logs

## Access Log

```bash
sudo tail -f /var/log/nginx/access.log
```

The access log records requests and HTTP status codes.

For example:

```text
GET /api/health HTTP/1.1" 429
```

indicates that the request received HTTP `429`.

## Error Log

```bash
sudo tail -f /var/log/nginx/error.log
```

The error log is useful when investigating Nginx configuration or upstream problems.

---

# 🛠️ Troubleshooting Approach

The project follows a layered troubleshooting approach.

```text
Client
  |
  v
Nginx :80
  |
  v
Flask :5007
```

If `/api/health` fails, test each layer independently.

### Test Flask directly

```bash
curl http://127.0.0.1:5007/health
```

### Test Nginx

```bash
curl http://127.0.0.1/api/health
```

### Validate Nginx

```bash
sudo nginx -t
```

### Check listening ports

```bash
sudo ss -lntp | grep -E ':80|:5007'
```

### Check logs

```bash
sudo tail -f /var/log/nginx/error.log
```

```bash
sudo tail -f /var/log/nginx/access.log
```

This makes it possible to determine whether the failure is at the application layer or the reverse-proxy layer instead of changing configuration randomly.

---

# 🎯 Week 1 Objectives

- [x] Install Nginx on Ubuntu EC2
- [x] Run Flask application
- [x] Configure Flask on port `5007`
- [x] Bind Flask to `127.0.0.1`
- [x] Configure Nginx reverse proxy
- [x] Serve static files
- [x] Configure proxy headers
- [x] Enable Gzip compression
- [x] Configure API rate limiting
- [x] Return HTTP `429`
- [x] Validate Nginx configuration
- [x] Test application routes
- [x] Verify Nginx logs
- [x] Verify Flask/Nginx integration

---

# 💼 DevOps Skills Demonstrated

This project demonstrates practical understanding of:

- Linux server administration
- AWS EC2
- Nginx
- Reverse proxy architecture
- HTTP request routing
- Static file serving
- Flask deployment
- Backend isolation
- HTTP headers
- Gzip compression
- Rate limiting
- HTTP status codes
- Service management with systemd
- Configuration validation
- Log-based troubleshooting
- Layer-by-layer debugging

---

# 🚀 Future Roadmap

This Week 1 project will be extended progressively.

## Week 2 — HTTPS & TLS

Planned:

- TLS fundamentals
- Let's Encrypt
- Certbot
- HTTPS
- HTTP → HTTPS redirect
- TLS 1.2 / TLS 1.3
- HTTP/2
- HSTS
- Certificate renewal
- TLS security testing

Target:

```text
Client
   |
   | HTTPS :443
   v
Nginx
   |
   | HTTP :5007
   v
Flask
```

## Week 3 — Load Balancing & Caching

Planned:

- Multiple Flask instances
- Nginx load balancing
- `least_conn`
- HAProxy
- Redis
- Application caching
- AWS Elastic Load Balancing

## Week 4 — Production-Style Capstone

Planned:

- UFW
- HTTPS
- HSTS
- Rate limiting
- Gzip
- Proxy caching
- Multiple Flask instances
- Health checks
- Redis
- AWS ALB
- Architecture documentation

---

# 📚 Key Learning

The most important concept from Week 1 is:

> **Nginx is the traffic-management layer in front of the application.**

The resulting architecture is:

```text
Internet
   |
   v
Nginx
   |
   +---- Static content
   |
   +---- Rate limiting
   |
   +---- Compression
   |
   +---- Reverse proxy
             |
             v
           Flask
             |
             v
        Application logic
```

This architecture provides the foundation for the HTTPS, load balancing, caching, and high-availability work planned in the next weeks.

# 🔐 Week 2 — HTTPS & TLS

Week 2 extends the Week 1 architecture by securing the public
connection between the client and Nginx.

#📅 Week 2 — HTTPS & TLS

Week 2 secures the public connection between the client and Nginx.

The architecture changed from:

Client
   |
   | HTTP :80
   v
Nginx

to:

Client
   |
   | HTTPS :443
   v
Nginx
🌍 1. DNS

A dedicated subdomain was created:

nginx.mangomansions.in

DNS A record:

nginx.mangomansions.in
        |
        v
52.66.145.89

Verification:

dig +short nginx.mangomansions.in

Expected:

52.66.145.89
Simple mental model

DNS answers:

"Where is this hostname?"

🏷️ 2. Nginx server_name

Nginx was configured for:

server_name nginx.mangomansions.in;

This tells Nginx which server configuration should handle requests for this hostname.

Important:

server_name nginx.mangomansions.in;

is an Nginx configuration directive, not a Linux command.

🔐 3. Let's Encrypt

Let's Encrypt is the Certificate Authority (CA) that issued the TLS certificate.

The certificate identifies:

nginx.mangomansions.in

Certificate information:

issuer  = Let's Encrypt, CN=YE1
subject = nginx.mangomansions.in

The CA's role is to issue/sign certificates after domain control has been validated.

🤖 4. Certbot

Certbot is the tool used to communicate with Let's Encrypt and manage the certificate.

Command:

sudo certbot --nginx -d nginx.mangomansions.in

Conceptually:

You
 |
 | certbot command
 v
Certbot
 |
 | ACME
 v
Let's Encrypt
 |
 | Domain validation
 |
 | Certificate issuance
 v
Certbot
 |
 +---- Install certificate
 |
 +---- Configure Nginx
 |
 +---- Configure renewal

The certificate files are available under:

/etc/letsencrypt/live/nginx.mangomansions.in/

Important files:

fullchain.pem
privkey.pem
Important security rule

Never commit:

privkey.pem
*.pem

or any private credentials to GitHub.

🔒 5. HTTPS and TLS

HTTPS is HTTP carried over TLS.

TLS provides:

Confidentiality

Others should not be able to read the encrypted traffic.

Integrity

Traffic should not be secretly modified without detection.

Authentication

The certificate helps establish that the server is the legitimate server for the requested domain.

The external connection is:

Browser
   |
   | HTTPS 🔒
   v
Nginx
🔐 6. TLS Termination

Nginx terminates TLS.

Browser
   |
   | HTTPS
   | encrypted
   v
Nginx
   |
   | HTTP
   | localhost
   v
Flask

Nginx receives the encrypted HTTPS connection, handles TLS, and then proxies the request to Flask.

This is called:

TLS termination at Nginx

↪️ 7. HTTP → HTTPS Redirect

HTTP requests arrive at:

TCP :80

Nginx returns a redirect such as:

HTTP/1.1 301 Moved Permanently
Location: https://nginx.mangomansions.in/

For example, if a user requests:

http://nginx.mangomansions.in/api/users

the flow is:

Browser
   |
   | HTTP :80
   v
Nginx
   |
   | 301 Moved Permanently
   | Location: https://...
   v
Browser
   |
   | NEW HTTPS :443 request
   v
Nginx
   |
   | proxy_pass
   v
Flask
Important concept

Nginx does not physically move the browser to HTTPS.

Nginx sends a 301 response telling the browser where to go.

The browser then makes a new HTTPS request.

🚀 8. HTTP/2

HTTP/2 is a newer HTTP protocol version that can improve connection efficiency.

Nginx was configured to support HTTP/2 on port 443.

Test:

curl -I --http2 https://nginx.mangomansions.in

Result:

HTTP/2 200
🤝 9. ALPN

ALPN stands for:

Application-Layer Protocol Negotiation

During the TLS handshake, the browser and Nginx negotiate the application protocol.

Conceptually:

Browser
   |
   | Supports:
   | h2
   | http/1.1
   v
Nginx
   |
   | Selects:
   | h2
   v
HTTP/2 connection

Important distinction:

TLS
 |
 +-- Provides secure connection
 |
 +-- During handshake:
       ALPN negotiates application protocol
                    |
                    v
                  HTTP/2

ALPN does not encrypt HTTP/2. TLS provides the secure channel.

🛡️ 10. HSTS

HSTS = HTTP Strict Transport Security.

Configured:

add_header Strict-Transport-Security "max-age=31536000" always;

The browser receives:

Strict-Transport-Security: max-age=31536000

31536000 seconds is approximately one year.

This tells a browser that has learned the policy to use HTTPS for the domain during the policy lifetime.

Verify:

curl -I https://nginx.mangomansions.in

Expected:

strict-transport-security: max-age=31536000
HSTS and Nginx

HSTS is sent as an HTTP response header by Nginx:

Nginx
  |
  | Strict-Transport-Security header
  v
Browser

It is not a separate network protocol.

🔒 11. TLS Version Hardening

Nginx was configured to allow:

ssl_protocols TLSv1.2 TLSv1.3;

Expected behavior:

TLS 1.0 → ❌ rejected
TLS 1.1 → ❌ rejected
TLS 1.2 → ✅ accepted
TLS 1.3 → ✅ accepted
Test TLS 1.2
openssl s_client \
  -connect nginx.mangomansions.in:443 \
  -servername nginx.mangomansions.in \
  -tls1_2
Test TLS 1.0
openssl s_client \
  -connect nginx.mangomansions.in:443 \
  -servername nginx.mangomansions.in \
  -tls1

TLS 1.0 and 1.1 handshake attempts failed, while TLS 1.2 and TLS 1.3 succeeded.

DevOps lesson

Changing configuration is not proof that the system works.

The process is:

Configure
   ↓
Test
   ↓
Observe actual behavior
   ↓
Confirm
🔎 12. Certificate Validation with OpenSSL
Issuer and Subject

Command:

sudo openssl x509 \
  -in /etc/letsencrypt/live/nginx.mangomansions.in/cert.pem \
  -noout \
  -issuer \
  -subject
Breaking down the command
openssl

Uses the OpenSSL toolkit.

x509

Tells OpenSSL that we are working with an X.509 certificate.

-in

Specifies the certificate file to read.

-in /etc/letsencrypt/live/nginx.mangomansions.in/cert.pem
-noout

Prevents OpenSSL from printing the entire certificate.

-issuer

Shows who issued the certificate.

-subject

Shows who the certificate represents.

Result:

issuer=Let's Encrypt, CN=YE1
subject=CN=nginx.mangomansions.in
🏷️ 13. Subject Alternative Name (SAN)

Command:

sudo openssl x509 \
  -in /etc/letsencrypt/live/nginx.mangomansions.in/cert.pem \
  -noout \
  -ext subjectAltName
What this command means

Read the X.509 certificate and show the Subject Alternative Name extension.

Result:

X509v3 Subject Alternative Name:
    DNS:nginx.mangomansions.in

This confirms that the certificate covers:

nginx.mangomansions.in

The SAN is an important part of hostname certificate validation.

🔄 14. Certificate Renewal

Certbot configured automatic renewal.

A dry-run renewal test was attempted:

sudo certbot renew --dry-run

The test encountered a temporary Let's Encrypt ACME rate/service limit:

rateLimited
Service busy; retry later

This did not invalidate the currently installed certificate.

The installed certificate was valid until:

2026-12-15

Certbot has a scheduled renewal mechanism.

🔍 15. OCSP Investigation

OCSP stands for:

Online Certificate Status Protocol

It is related to checking certificate status/revocation.

We checked whether the certificate contains an OCSP responder URI:

sudo openssl x509 \
  -in /etc/letsencrypt/live/nginx.mangomansions.in/cert.pem \
  -noout \
  -ocsp_uri

No OCSP URI was returned.

The certificate's Authority Information Access contained:

CA Issuers - URI:http://ye1.i.lencr.org/

This is a CA Issuers URI, not an OCSP responder URI.

We also checked Nginx:

sudo nginx -T | grep -E \
"ssl_trusted_certificate|ssl_stapling|ssl_stapling_verify"

No matching stapling configuration was present.

Therefore, OCSP stapling was not blindly enabled for this certificate.

🌐 16. Final External HTTPS Validation

The final validation was performed from the Mac, representing an external client.

HTTPS
curl -I https://nginx.mangomansions.in

Result:

HTTP/2 200
server: nginx/1.24.0 (Ubuntu)
strict-transport-security: max-age=31536000
HTTP/2
curl -I --http2 https://nginx.mangomansions.in

Result:

HTTP/2 200
server: nginx/1.24.0 (Ubuntu)
strict-transport-security: max-age=31536000

This confirmed that the public HTTPS path works from outside the EC2 instance.

📊 Week 2 Status
Feature	Status
DNS A record	✅
Let's Encrypt certificate	✅
Certbot	✅
HTTPS :443	✅
HTTP → HTTPS redirect	✅
TLS termination	✅
HTTP/2	✅
ALPN / HTTP/2 negotiation	✅
HSTS	✅
TLS 1.2	✅
TLS 1.3	✅
TLS 1.0 rejected	✅
TLS 1.1 rejected	✅
Certificate SAN	✅
External HTTPS testing	✅
Automatic renewal configuration	✅
OCSP investigation	✅
🧠 Week 2 Mental Model
                    INTERNET
                       |
             nginx.mangomansions.in
                       |
                      DNS
                       |
                 52.66.145.89
                       |
            +----------+----------+
            |                     |
        HTTP :80              HTTPS :443
            |                     |
            v                     v
         Nginx                  Nginx
            |                     |
       301 redirect          TLS handshake
            |                Certificate
            v                     |
         Browser                ALPN
                                  |
                               HTTP/2
                                  |
                                  v
                           TLS termination
                                  |
                                  | HTTP
                                  v
                            Flask :5007
🔑 Week 2 Key Concepts
DNS
→ Where is my server?

Certificate
→ Which domain does this certificate represent?

Let's Encrypt
→ Certificate Authority that issues the certificate.

Certbot
→ Tool that communicates with Let's Encrypt and manages the certificate.

TLS
→ Provides secure communication.

HTTPS
→ HTTP over TLS.

TLS termination
→ Nginx handles the external TLS connection.

HTTP/2
→ HTTP protocol version used after negotiation.

ALPN
→ Negotiates the application protocol during TLS.

HSTS
→ Tells a browser to use HTTPS for the domain.

OCSP
→ Certificate status/revocation mechanism.
🔐 Security Rules

Never commit:

*.pem
privkey.pem
*.key
.env
AWS credentials
API keys
passwords

The EC2 private key must remain local.

📁 Project Structure
nginx-flask-reverse-proxy/
│
├── app/
│   ├── app.py
│   └── requirements.txt
│
├── nginx/
│   └── nginx.conf
│
├── scripts/
│   └── setup.sh
│
├── static/
│   └── index.html
│
├── tests/
│   └── test_routes.sh
│
├── .gitignore
└── README.md

Nginx Week 3
Nginx Week 4
Nginx Week 5

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
