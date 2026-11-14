# BusReserve 2.0 — System Architecture & Technical Design

## 1. System Architecture Diagram

```mermaid
flowchart TD
    ClientHTTP["Client Browser / REST Client\n(HTTP :8080)"] --> Nginx
    ClientHTTPS["Client Browser / REST Client\n(HTTPS :8443 TLS 1.2/1.3)"] --> Nginx

    subgraph Host["Docker Host (Local Machine / Linux VM - ₹0/Month Parity)"]
        subgraph DockerNet["Isolated Bridge Network (busreserve_net)"]
            Nginx["Nginx 1.27 Reverse Proxy\n(:80 & :443 internal | :8080 & :8443 host)\nTLS Termination, Rate Limiting & Security Headers"]

            Nginx -->|"/" (React SPA)| Frontend["Frontend Container (Nginx)\n(:80 internal)"]
            Nginx -->|"/api/*"\n"/health/*"\n"/metrics"| Backend["Backend API Container (Flask 3.1 + Gunicorn 23.0)\n(:5000 internal | non-root uid=10001)"]
            Backend -->|"SQLAlchemy / psycopg2\n(FOR UPDATE + Partial Unique Index)"| Postgres[("PostgreSQL 16 Database\n(:5432 internal | unexposed)")]
            Postgres --- Volume[("Persistent Volume\nbusreserve_pgdata")]
        end
    end

    subgraph ObservabilityStack["Built-in Observability & Monitoring"]
        Backend --> Prom["Prometheus Metrics (/metrics)\n(Connection Pools, Latency Histograms, RPS)"]
        Prom --> Graf["Grafana Dashboard JSON\n(busreserve_dashboard.json)"]
        Prom --> Alert["Alertmanager Rules\n(alert_rules.yml)"]
    end
```

---

## 2. Component Responsibilities

| Component | Technology | Responsibility |
| :--- | :--- | :--- |
| **Reverse Proxy** | `nginx:1.27-alpine` | Single public ingress (`:8080` HTTP, `:8443` HTTPS), terminates TLS 1.2/1.3, routes `/` to SPA frontend, proxies `/api/`, `/health/`, and `/metrics` to Flask backend with `X-Request-ID`, `X-Forwarded-*`, security headers (`nosniff`, `SAMEORIGIN`, CSP), and bounded timeouts. |
| **Frontend SPA** | React 18, Vite 6, Tailwind CSS, Lucide Icons, React Router | Responsive UI for route search, interactive 2+2 coach seat map, passenger reservation form, PNR lookup/cancellation, and masked-PII operational demo overview. |
| **Backend API** | Python 3.12, Flask 3.1, Flask-SQLAlchemy, Flask-Migrate, Marshmallow, Gunicorn | Modular Flask app factory providing REST endpoints, strict request schema validation, structured JSON logging with `request_id`, liveness/readiness probes, and atomic booking transactions. Executes as non-root `uid=10001(appuser)`. |
| **Database** | PostgreSQL 16 | Stores routes, ordered stops, scheduled trips, seat inventory, and bookings on persistent volume `busreserve_pgdata`, enforcing double-booking prevention at the engine level. |

---

## 3. Network & Security Boundaries

1. **Host Ingress**: Only Nginx publishes ports on the host (`8080` HTTP, `8443` HTTPS). All other services bind strictly inside `busreserve_net`.
2. **PostgreSQL Isolation**: PostgreSQL port `5432` is unexposed to the host network, mitigating external brute-force and network eavesdropping risks.
3. **Least Privilege Containerization**: The backend runs as non-root user `uid=10001(appuser)`. Nginx drops privileges from master process to `nginx` user for worker processes.
4. **Header Enforcement**: Nginx automatically injects:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: SAMEORIGIN`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - `Content-Security-Policy: default-src 'self' ...`
   - `Permissions-Policy: geolocation=(), camera=(), microphone=(), payment=()`
   - `Cross-Origin-Opener-Policy: same-origin`
5. **Correlation Tracking**: Nginx maps `$http_x_request_id` to `$correlation_id` (or generates a UUID4), passing it to Flask via `X-Request-ID` and returning it in all HTTP responses.

---

## 4. Concurrent Booking Protection (Pessimistic Locking Sequence)

```mermaid
sequenceDiagram
    autonumber
    actor User1 as User A (Thread 1)
    actor User2 as User B (Thread 2)
    participant Nginx as Nginx Reverse Proxy (:8443)
    participant API as Flask Backend (Gunicorn)
    participant DB as PostgreSQL 16 Engine

    Note over User1,User2: Simultaneous contention for Seat 1A on Trip 4

    par User A Requests Seat 1A
        User1->>Nginx: POST /api/bookings (Trip 4, Seat 1A)
        Nginx->>API: Proxy with X-Request-ID
        API->>DB: BEGIN Transaction
        API->>DB: SELECT * FROM trip_seats WHERE trip_id=4 AND seat_number='1A' FOR UPDATE
        Note over DB: Lock acquired by User A
    and User B Requests Seat 1A
        User2->>Nginx: POST /api/bookings (Trip 4, Seat 1A)
        Nginx->>API: Proxy with X-Request-ID
        API->>DB: BEGIN Transaction
        API->>DB: SELECT * FROM trip_seats WHERE trip_id=4 AND seat_number='1A' FOR UPDATE
        Note over DB: User B BLOCKS on row lock until User A completes
    end

    API->>DB: Check active booking for Seat 1A (None found)
    API->>DB: INSERT INTO bookings (pnr='BR...', trip_id=4, seat_id=..., status='CONFIRMED')
    API->>DB: COMMIT Transaction
    Note over DB: Lock released. Partial Unique Index enforced.
    API-->>Nginx: HTTP 201 Created (Confirmed Booking & PNR)
    Nginx-->>User1: HTTP 201 Created (Booking Success)

    Note over DB: User B resumes execution
    API->>DB: Check active booking for Seat 1A (Found User A's confirmed booking!)
    API->>DB: ROLLBACK Transaction
    API-->>Nginx: HTTP 409 Conflict ("Seat 1A is already booked")
    Nginx-->>User2: HTTP 409 Conflict (Safe Failure, Zero Duplicates)
```

---

## 5. Database Schema & Relational Model

```mermaid
erDiagram
    routes ||--o{ route_stops : "has ordered"
    routes ||--o{ trips : "schedules"
    trips ||--o{ trip_seats : "contains"
    trips ||--o{ bookings : "receives"
    trip_seats ||--o{ bookings : "reserved by"
    route_stops ||--o{ bookings : "boarding / drop"
    users ||--o{ bookings : "owns"
    bookings ||--o{ payment_transactions : "paid via"

    routes {
        int id PK
        varchar name UK
        varchar source
        varchar destination
    }
    route_stops {
        int id PK
        int route_id FK
        varchar stop_name
        int stop_order
    }
    trips {
        int id PK
        int route_id FK
        varchar operator_name
        varchar bus_number
        time departure_time
        time arrival_time
        date travel_date
        numeric base_fare
        varchar status
    }
    trip_seats {
        int id PK
        int trip_id FK
        varchar seat_number
        varchar seat_type
    }
    bookings {
        int id PK
        varchar pnr UK
        int trip_id FK
        int seat_id FK
        int user_id FK
        varchar passenger_name
        varchar passenger_email
        varchar passenger_phone
        int boarding_stop_id FK
        int drop_stop_id FK
        numeric total_fare
        varchar status
        varchar refund_status
        timestamptz created_at
    }
    payment_transactions {
        int id PK
        int booking_id FK
        varchar transaction_ref UK
        varchar gateway
        numeric amount
        varchar status
        timestamptz created_at
    }
```

### Critical Concurrency Guarantee

Two concurrent users can never reserve the same `(trip_id, seat_id)`:

1. **Row-level pessimistic lock**: `create_booking` queries `trip_seats` with `SELECT ... FOR UPDATE OF trip_seats` inside a PostgreSQL transaction.
2. **Database-level partial unique index**:
   ```sql
   CREATE UNIQUE INDEX uq_active_booking_trip_seat
   ON bookings (trip_id, seat_id)
   WHERE (status = 'CONFIRMED');
   ```
   Even if two independent sessions attempt simultaneous inserts without row locking, PostgreSQL rejects the second `CONFIRMED` row with a `23505` unique violation (`uq_active_booking_trip_seat`), which the API translates cleanly to `HTTP 409 Conflict` after rolling back.
3. **PNR atomicity & rebooking**: PNRs are generated inside the transaction; failed attempts leave zero orphaned rows. Cancelling changes `status` to `CANCELLED`, preserving audit history while immediately making the seat eligible for a new `CONFIRMED` booking.
