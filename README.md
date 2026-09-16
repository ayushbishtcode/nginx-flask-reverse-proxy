# 🚀 Nginx Flask Reverse Proxy

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
