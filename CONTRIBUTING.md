# Contributing to BusReserve 2.0

Thank you for your interest in contributing to **BusReserve 2.0**! We welcome contributions from the community to improve performance, enhance security, and expand transit capabilities.

---

## 1. Code of Conduct

All contributors are expected to uphold a welcoming, respectful, and harassment-free environment for everyone, regardless of experience level, identity, or background.

---

## 2. Development Workflow

### A. Fork & Clone
1. Fork the repository to your GitHub account: `https://github.com/satyam-verse/busreserve-2.0`
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/busreserve-2.0.git
   cd busreserve-2.0
   ```
3. Create a descriptive feature branch:
   ```bash
   git checkout -b feature/dynamic-fare-pricing
   ```

### B. Environment Setup
1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
2. Launch the local containerized stack:
   ```bash
   # Windows PowerShell
   .\scripts\setup_clean_environment.ps1

   # Linux / macOS Bash
   ./scripts/setup_clean_environment.sh
   ```
3. Verify local services:
   - Frontend SPA: [http://localhost:8080](http://localhost:8080)
   - HTTPS Gateway: [https://localhost:8443](https://localhost:8443)
   - Health Probe: [https://localhost:8443/health/ready](https://localhost:8443/health/ready)
   - Prometheus Metrics: [https://localhost:8443/metrics](https://localhost:8443/metrics)

---

## 3. Code Standards & Quality Gates

Every pull request must pass the automated CI/CD pipeline before merging.

### Python Backend Standards
- **Python Version**: 3.12+
- **Code Formatter & Linter**: **Ruff**
  ```bash
  cd backend
  ruff format --check .
  ruff check .
  ```
- **Automated Testing**: **pytest**
  ```bash
  cd backend
  pytest tests/ -v
  ```
- **Dependency Audit**:
  ```bash
  pip-audit
  ```

### React Frontend Standards
- **Node Version**: 20+
- **Framework**: React 18 with Vite and Tailwind CSS
- **Linting & Build Verification**:
  ```bash
  cd frontend
  npm ci
  npm run build
  ```

---

## 4. Git Commit Message Guidelines

We follow the Conventional Commits specification:

```
<type>(<scope>): <short description>

[optional longer body explaining context and rationale]

[optional footer(s), e.g., Closes #12]
```

### Allowed Types:
- `feat`: A new user-facing feature or API capability.
- `fix`: A bug fix or patch.
- `docs`: Documentation updates or additions.
- `style`: Formatting changes that do not alter code logic.
- `refactor`: Code refactoring without behavioral modification.
- `perf`: Performance optimizations.
- `test`: Adding or updating test cases.
- `chore`: Maintenance tasks, dependency updates, CI/CD pipeline adjustments.

### Examples:
- `feat(payment): add mock netbanking gateway provider`
- `fix(concurrency): prevent race condition during simultaneous seat selection`
- `perf(trips): add composite index for source and destination city lookups`

---

## 5. Submitting Pull Requests

1. Ensure your branch is rebased onto the latest `master` or `main` branch.
2. Verify that all 55 backend tests pass and frontend build succeeds.
3. Open a Pull Request pointing to `satyam-verse/busreserve-2.0` (`master` branch).
4. Provide a clear description of changes, motivation, and manual test evidence.
5. All CI checks (linting, tests, container build, Trivy security scan) must be green.
6. A repository maintainer will review your PR and provide feedback.
