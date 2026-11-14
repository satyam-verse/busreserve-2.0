# Security Policy — BusReserve 2.0

## 1. Supported Versions

Security updates and vulnerability remediation are actively maintained on the following branches:

| Version | Supported | Status |
| :--- | :---: | :--- |
| **2.0.x** | :white_check_mark: | Current Production / Active Maintenance |
| 1.0.x | :x: | Deprecated Baseline MVP |

---

## 2. Reporting a Vulnerability

We prioritize the security of the BusReserve 2.0 reservation platform and its users. If you discover a security vulnerability, **please do NOT create a public GitHub issue**.

### Reporting Process:
1. Email details of the vulnerability to: **`security@busreserve.local`** or contact the repository owner privately via GitHub Private Vulnerability Reporting.
2. Include:
   - Vulnerability category (e.g., IDOR, SQL injection, concurrency race condition, XSS, SSRF).
   - Step-by-step reproduction instructions or a minimal proof of concept (PoC).
   - Affected endpoints, parameters, or components.
   - Assessment of potential impact.
3. You will receive an acknowledgment within **24 hours**, along with a remediation timeline.
4. Once the patch is validated and deployed, public credit will be acknowledged in release notes with your consent.

---

## 3. Defense-in-Depth Architecture & Controls

BusReserve 2.0 implements layered security controls across all architectural tiers:

### A. Network & Ingress Security
- **Reverse Proxy Barrier**: All traffic enters through an Nginx 1.27 reverse proxy. The Flask backend, PostgreSQL database, and frontend build containers have **no exposed ports** on the public host network; they communicate strictly over an isolated Docker bridge network (`busreserve_net`).
- **TLS 1.2 / 1.3 Strict Ciphers**: Weak SSL/TLS ciphers and protocols are disabled. Forward secrecy is enforced with ECDHE suites.
- **Harden Ingress Headers**: Every response is fortified with:
  - `Content-Security-Policy: default-src 'self' ...`
  - `X-Frame-Options: SAMEORIGIN`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy: geolocation=(), camera=(), microphone=()`

### B. Authentication & Session Management
- **Stateless & Cookie-Based JWT**: Authentication tokens are signed with HMAC-SHA256 using an isolated 32-byte cryptographic secret key.
- **HttpOnly & SameSite Protection**: Tokens are transmitted via `HttpOnly`, `SameSite=Lax` cookies to prevent client-side JavaScript access and mitigate Cross-Site Scripting (XSS) and Cross-Site Request Forgery (CSRF).
- **Password Hashing**: Passwords are cryptographically hashed using PBKDF2 with SHA-256 and salted work factors. Plaintext passwords are never logged or stored.
- **RBAC Enforcement**: Strict role separation isolates Passenger endpoints (`ROLE_USER`) from Administrative fleet control endpoints (`ROLE_ADMIN`). Unauthorized privilege escalation returns `HTTP 403 Forbidden`.

### C. Financial & Transactional Integrity
- **Concurrency & Double-Booking Protection**: Seat reservations enforce pessimistic locking (`SELECT ... FOR UPDATE`) in conjunction with a PostgreSQL partial unique index (`idx_trip_seat_active_booking`). Simultaneous booking attempts on the same seat fail safely with `HTTP 409 Conflict`.
- **Cryptographic Payment Settlement**: Checkout tokens are cryptographically validated against tamper-proof HMAC signatures before booking issuance.
- **Zero Raw Card Data**: Credit/debit card numbers and CVVs are never handled directly by the application; transactions operate via mock/tokenized gateways adhering to PCI-DSS compliance principles.

### D. Centralized Structured Logging & Sanitization
- **PII & Secret Scrubbing**: A custom JSON log formatter intercepts all log records. Any sensitive key (e.g., `password`, `token`, `secret`, `card_number`, `cvv`, `auth_header`) is automatically masked before emission.
- **Correlation IDs**: Every incoming request is assigned a unique `X-Request-ID` UUID, propagated through Nginx and Flask for end-to-end distributed tracing.

### E. Container Security
- **Least Privilege Execution**: The backend container runs under an unprivileged user (`appuser`, UID `10001`), preventing container-breakout escalation.
- **Automated Container Scanning**: Continuous integration pipelines scan container images with **Trivy** to intercept CRITICAL and HIGH severity vulnerabilities before publishing to GitHub Container Registry (GHCR).
