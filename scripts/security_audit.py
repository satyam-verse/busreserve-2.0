"""BusReserve 2.0 - Security Audit & Secret Leak Scanner for GitHub Publication.

Scans the entire repository:
1. Working directory source code, config files, documentation, and scripts.
2. Excludes .git, .venv, node_modules, and dist.
3. Checks for high-risk secret patterns:
   - Google API Keys (AIzaSy...)
   - AWS Access Key IDs (AKIA...)
   - GitHub Personal Access Tokens (ghp_, gho_, ghu_, ghs_, ghr_)
   - Stripe / Razorpay Secret Keys (sk_live_, rzp_live_)
   - Generic API Key / Secret assignments with high entropy
   - Private Keys (-----BEGIN ... PRIVATE KEY-----)
   - Real passwords or database credentials
4. Inspects Git history (commits, trees, blobs) for past leaks.
"""

import os
import re
import subprocess
import sys

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "coverage",
    "htmlcov",
}

IGNORED_EXTENSIONS = {
    ".pyc",
    ".png",
    ".jpg",
    ".jpeg",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".pdf",
}

PATTERNS = [
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("AWS Access Key ID", re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}")),
    ("GitHub Token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}")),
    ("Stripe Secret Key", re.compile(r"sk_live_[0-9a-zA-Z]{24,}")),
    ("Razorpay Secret Key", re.compile(r"rzp_live_[0-9a-zA-Z]{14,}")),
    ("Private Key Header", re.compile(r"-----BEGIN\s+(?:RSA|DSA|EC|OPENSSH|PGP|ENCRYPTED|PRIVATE)?\s*KEY-----")),
    ("Database URL with Password", re.compile(r"(?:postgres|postgresql|mysql)://[^:]+:([a-zA-Z0-9_!@#$%^&*()+=]+)@[a-zA-Z0-9.-]+:\d+/")),
    ("Generic Secret Assignment", re.compile(r"(?:api_key|apikey|secret_key|jwt_secret|private_key|auth_token)\s*=\s*['\"][0-9a-zA-Z\-_]{20,}['\"]", re.IGNORECASE)),
]

SAFE_WHITELIST = {
    "replace-with-strong-random-secret-32b",
    "replace-with-strong-jwt-secret-32b",
    "dev-insecure-secret-key-change-in-production-32b",
    "dev-jwt-only-change-in-production",
    "your-gemini-api-key-here",
    "busreserve_dev_change_me",
    "busreserve_dev",
}


def scan_working_directory(root_dir: str):
    findings = []
    files_scanned = 0

    for root, dirs, files in os.walk(root_dir):
        # Exclude ignored dirs in-place
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith(".")]

        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in IGNORED_EXTENSIONS:
                continue

            fpath = os.path.join(root, fname)
            rel_path = os.path.relpath(fpath, root_dir)

            # Skip untracked local SSL certs and .env file
            if rel_path in {".env", os.path.join("nginx", "certs", "selfsigned.crt"), os.path.join("nginx", "certs", "selfsigned.key")}:
                continue

            files_scanned += 1
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for pat_name, pattern in PATTERNS:
                    matches = pattern.finditer(content)
                    for m in matches:
                        matched_str = m.group(0)
                        # Check whitelist
                        if any(whitelisted in matched_str for whitelisted in SAFE_WHITELIST):
                            continue
                        
                        # Calculate line number
                        line_no = content[:m.start()].count("\n") + 1
                        snippet = content.splitlines()[line_no - 1]
                        findings.append({
                            "type": pat_name,
                            "file": rel_path,
                            "line": line_no,
                            "snippet": snippet.strip()[:100],
                            "match": matched_str[:20] + "..." if len(matched_str) > 20 else matched_str
                        })
            except Exception as e:
                pass

    return files_scanned, findings


def scan_git_history():
    history_findings = []
    try:
        proc = subprocess.run(
            ["git", "log", "-p", "--all"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        diff_text = proc.stdout
        for pat_name, pattern in PATTERNS:
            matches = pattern.finditer(diff_text)
            for m in matches:
                matched_str = m.group(0)
                if any(whitelisted in matched_str for whitelisted in SAFE_WHITELIST):
                    continue
                history_findings.append({
                    "type": pat_name,
                    "match": matched_str[:20] + "..."
                })
    except Exception as e:
        history_findings.append({"type": "Git scan error", "match": str(e)})

    return history_findings


if __name__ == "__main__":
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"Scanning repository at: {root}")
    scanned_count, findings = scan_working_directory(root)
    git_findings = scan_git_history()

    print(f"Total files scanned: {scanned_count}")
    print(f"Working tree findings: {len(findings)}")
    print(f"Git history findings: {len(git_findings)}")

    if findings:
        print("\n[ALERT] Working directory security findings:")
        for f in findings:
            print(f"  - [{f['type']}] {f['file']}:{f['line']} -> {f['match']} (Snippet: {f['snippet']})")

    if git_findings:
        print("\n[ALERT] Git history security findings:")
        for gf in git_findings:
            print(f"  - [{gf['type']}] -> {gf['match']}")

    if not findings and not git_findings:
        print("\n[PASSED] Zero security findings! No exposed credentials or secrets detected.")
