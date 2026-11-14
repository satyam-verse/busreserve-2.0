"""Generate self-signed SSL/TLS certificates for local HTTPS Nginx testing.

This script creates a 2048-bit RSA private key and a self-signed X.509
certificate valid for 365 days with Subject Alternative Names (SAN)
for localhost, 127.0.0.1, and ::1.
"""

from datetime import datetime, timedelta, timezone
import ipaddress
import os
import sys

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:
    print(
        "ERROR: 'cryptography' library is required to generate certificates.",
        file=sys.stderr,
    )
    print(
        "Run this script via backend container: docker exec -i busreserve-backend python /app/scripts/... or install cryptography.",
        file=sys.stderr,
    )
    sys.exit(1)


def generate_certificates(
    output_dir: str, cert_name: str = "selfsigned.crt", key_name: str = "selfsigned.key"
):
    os.makedirs(output_dir, exist_ok=True)
    cert_path = os.path.join(output_dir, cert_name)
    key_path = os.path.join(output_dir, key_name)

    print("Generating 2048-bit RSA private key...")
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Karnataka"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Bengaluru"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Algions AI Labs"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "DevOps Engineering"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ]
    )

    san = x509.SubjectAlternativeName(
        [
            x509.DNSName("localhost"),
            x509.DNSName("*.localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
            x509.IPAddress(ipaddress.IPv6Address("::1")),
        ]
    )

    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(san, critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(key, hashes.SHA256(), default_backend())
    )

    # Write private key
    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    print(f"Private key written to: {key_path}")

    # Write certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    print(f"Certificate written to: {cert_path}")

    print("Successfully generated local SSL/TLS certificate pair.")
    return cert_path, key_path


if __name__ == "__main__":
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "nginx/certs"
    generate_certificates(target_dir)
