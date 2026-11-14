"""Phase 3 Frontend Implementation Screenshot Capture Utility.

Uses Chrome DevTools Protocol to capture clean high-resolution screenshots of all
Phase 3 frontend features and interactive states into the conversation artifact directory.
"""

import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

try:
    from scripts.auth_helpers import get_demo_credentials
except ModuleNotFoundError:
    from auth_helpers import get_demo_credentials

if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://localhost:8080"
HTTPS_BASE_URL = "https://localhost:8443"
ARTIFACT_DIR = r"C:\Users\iamsa\.gemini\antigravity\brain\823d2f68-3896-44b0-8a5c-501a4a84ade6"
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
CDP_PORT = 9258


class SimpleCDP:
    def __init__(self, ws_url: str):
        rest = ws_url[len("ws://") :]
        host_port, path = rest.split("/", 1)
        host, port = host_port.split(":")
        self.sock = socket.create_connection((host, int(port)), timeout=25)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET /{path} HTTP/1.1\r\n"
            f"Host: {host_port}\r\n"
            f"Origin: http://{host_port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(req.encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        assert b" 101 " in buf, f"Unexpected WS handshake: {buf!r}"
        self.extra = buf.split(b"\r\n\r\n", 1)[1]
        self._msg_id = 0

    def _recv_exact(self, n: int) -> bytes:
        out = bytearray()
        if self.extra:
            take = min(n, len(self.extra))
            out.extend(self.extra[:take])
            self.extra = self.extra[take:]
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise ConnectionError("WebSocket closed")
            out.extend(chunk)
        return bytes(out)

    def _recv_frame(self) -> tuple[int, bytes]:
        b1, b2 = self._recv_exact(2)
        opcode = b1 & 0x0F
        masked = (b2 & 0x80) != 0
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        mask_key = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    def _send_text(self, text: str) -> None:
        raw = text.encode("utf-8")
        mask = os.urandom(4)
        header = bytearray([0x81])
        n = len(raw)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", n))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", n))
        header.extend(mask)
        masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(raw))
        self.sock.sendall(bytes(header) + masked_payload)

    def call(self, method: str, params: dict | None = None):
        self._msg_id += 1
        target_id = self._msg_id
        self._send_text(json.dumps({"id": target_id, "method": method, "params": params or {}}))
        while True:
            opcode, payload = self._recv_frame()
            if opcode == 0x8:
                raise ConnectionError("WS closed by target")
            if opcode != 0x1:
                continue
            msg = json.loads(payload.decode("utf-8"))
            if msg.get("id") == target_id:
                if "error" in msg:
                    raise RuntimeError(f"CDP error for {method}: {msg['error']}")
                return msg.get("result", {})

    def eval_js(self, expr: str):
        res = self.call(
            "Runtime.evaluate",
            {"expression": expr, "awaitPromise": True, "returnByValue": True},
        )
        return res.get("result", {}).get("value")

    def navigate(self, url: str, wait_secs: float = 1.5):
        self.call("Page.navigate", {"url": url})
        time.sleep(wait_secs)

    def screenshot(self, filename: str) -> str:
        res = self.call("Page.captureScreenshot", {"format": "png"})
        out_path = os.path.join(ARTIFACT_DIR, filename)
        with open(out_path, "wb") as f:
            f.write(base64.b64decode(res["data"]))
        print(f"  [SAVED] {filename} ({os.path.getsize(out_path):,} bytes)")
        return out_path

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def main():
    print("=== BusReserve 2.0 - Phase 3 Visual Evidence Capture ===")

    # Ensure demo public share token exists for screenshot
    share_token = "QZz6EFkd-80tj7nOItoljh67marQnNybGWif21022T0"
    admin_pw, user_pw = get_demo_credentials()
    try:
        # Create an active journey share on trip 4 for testing
        login_payload = json.dumps({"email": "passenger@busreserve.local", "password": user_pw}).encode()
        req = urllib.request.Request(f"{BASE_URL}/api/auth/login", data=login_payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as res:
            login_data = json.loads(res.read())
            token = login_data.get("token") or login_data.get("access_token")

        req = urllib.request.Request(f"{BASE_URL}/api/user/bookings", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req) as res:
            bookings = json.loads(res.read()).get("bookings", [])
            if bookings:
                booking_id = bookings[0]["id"]
                share_payload = json.dumps({"booking_id": booking_id, "validity_hours": 48}).encode()
                req = urllib.request.Request(f"{BASE_URL}/api/tracking/share", data=share_payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
                with urllib.request.urlopen(req) as s_res:
                    s_data = json.loads(s_res.read())
                    share_token = s_data.get("token", share_token)
    except Exception as e:
        print(f"Note on share token setup: {e}")

    user_data_dir = tempfile.mkdtemp(prefix="busreserve_phase3_scr_")
    chrome_proc = subprocess.Popen(
        [
            CHROME_PATH,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            f"--remote-debugging-port={CDP_PORT}",
            "--remote-allow-origins=*",
            f"--user-data-dir={user_data_dir}",
            "--window-size=1440,960",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        targets = None
        for _ in range(40):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{CDP_PORT}/json") as resp:
                    targets = json.loads(resp.read().decode())
                    if targets:
                        break
            except Exception:
                time.sleep(0.3)

        assert targets, "Chrome CDP did not start"
        page_target = next(t for t in targets if t.get("type") == "page")
        cdp = SimpleCDP(page_target["webSocketDebuggerUrl"])
        cdp.call("Runtime.enable")
        cdp.call("Page.enable")
        cdp.call("Network.enable")

        # -------------------------------------------------------------
        # 1. Seat Tiers & Cheapest Seat Finder (/trips/1/seats)
        # -------------------------------------------------------------
        print("\n1. Capturing Seat Selection, Premium Badges & Cheapest Seat Finder...")
        cdp.navigate(f"{BASE_URL}/trips/1/seats", wait_secs=2.0)
        # Click on a Premium seat (e.g. 1A) to display Selected Seat Summary with Amenities & transparent price
        cdp.eval_js("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn1A = buttons.find(b => b.textContent.includes('1A'));
                if (btn1A) btn1A.click();
            })()
        """)
        time.sleep(0.8)
        cdp.screenshot("phase3_01_seat_tiers_and_cheapest_finder.png")

        # -------------------------------------------------------------
        # 2. Login Passenger & Passenger Dashboard with Tracking & Sharing Modals
        # -------------------------------------------------------------
        print("\n2. Logging in Passenger & Capturing Live Tracking Modal...")
        cdp.navigate(f"{BASE_URL}/login", wait_secs=1.0)
        cdp.eval_js("""
            (() => {
                const emailInput = document.querySelector('input[type="email"]');
                const pwInput = document.querySelector('input[type="password"]');
                if (emailInput && pwInput) {
                    const setVal = (el, val) => {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        setter.call(el, val);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    };
                    setVal(emailInput, 'passenger@busreserve.local');
                    setVal(pwInput, {json.dumps(user_pw)});
                    const form = emailInput.closest('form');
                    if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                }
            })()
        """)
        time.sleep(2.0)

        # Navigate to bookings and trigger Track Bus modal
        cdp.navigate(f"{BASE_URL}/dashboard/bookings", wait_secs=2.0)
        cdp.eval_js("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const trackBtn = buttons.find(b => b.textContent.includes('Track Bus'));
                if (trackBtn) trackBtn.click();
            })()
        """)
        time.sleep(2.0)
        cdp.screenshot("phase3_02_passenger_live_tracking_modal.png")

        # Close tracking modal and open Share Journey modal
        cdp.eval_js("""
            (() => {
                const closeBtn = document.querySelector('button[aria-label="Close modal"]') || document.querySelector('button:has(svg)');
                if (closeBtn) closeBtn.click();
            })()
        """)
        time.sleep(0.5)

        print("\n3. Capturing Share Journey Modal...")
        cdp.eval_js("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const shareBtn = buttons.find(b => b.textContent.includes('Share'));
                if (shareBtn) shareBtn.click();
            })()
        """)
        time.sleep(1.0)
        # Click Generate Link inside modal
        cdp.eval_js("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const genBtn = buttons.find(b => b.textContent.includes('Generate') || b.textContent.includes('Tracking Link'));
                if (genBtn) genBtn.click();
            })()
        """)
        time.sleep(1.5)
        cdp.screenshot("phase3_03_passenger_share_journey_modal.png")

        # -------------------------------------------------------------
        # 4. Public Journey Tracking Page (/journey/track/:token)
        # -------------------------------------------------------------
        print("\n4. Capturing Public Journey Tracking Page (Zero PII)...")
        cdp.navigate(f"{BASE_URL}/journey/track/{share_token}", wait_secs=2.5)
        cdp.screenshot("phase3_04_public_journey_track_page.png")

        # -------------------------------------------------------------
        # 5. Driver GPS Console (/driver)
        # -------------------------------------------------------------
        print("\n5. Logging in Admin & Capturing Driver GPS Console...")
        cdp.navigate(f"{BASE_URL}/admin/login", wait_secs=1.0)
        cdp.eval_js("""
            (() => {
                const emailInput = document.querySelector('input[type="email"]');
                const pwInput = document.querySelector('input[type="password"]');
                if (emailInput && pwInput) {
                    const setVal = (el, val) => {
                        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        setter.call(el, val);
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    };
                    setVal(emailInput, 'admin@busreserve.local');
                    setVal(pwInput, {json.dumps(admin_pw)});
                    const form = emailInput.closest('form');
                    if (form) form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
                }
            })()
        """)
        time.sleep(2.0)

        cdp.navigate(f"{BASE_URL}/driver", wait_secs=2.0)
        # Send a simulated ping to populate the HUD gauges
        cdp.eval_js("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const testBtn = buttons.find(b => b.textContent.includes('Send Single Test Ping'));
                if (testBtn) testBtn.click();
            })()
        """)
        time.sleep(1.5)
        cdp.screenshot("phase3_05_driver_gps_console.png")

        # -------------------------------------------------------------
        # 6. Operator Fleet Dashboard & Takeover Modal (/operator)
        # -------------------------------------------------------------
        print("\n6. Capturing Operator Fleet Dashboard & Takeover Modal...")
        cdp.navigate(f"{BASE_URL}/operator", wait_secs=2.0)
        # Open Takeover modal on first bus
        cdp.eval_js("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const takeoverBtn = buttons.find(b => b.textContent.includes('Takeover GPS'));
                if (takeoverBtn) takeoverBtn.click();
            })()
        """)
        time.sleep(1.0)
        cdp.screenshot("phase3_06_operator_fleet_dashboard.png")

        # -------------------------------------------------------------
        # 7. Smart Notifications Dropdown (Navbar Bell)
        # -------------------------------------------------------------
        print("\n7. Capturing Smart Notifications Bell & Dropdown Feed...")
        # Close modal and click notification bell
        cdp.eval_js("""
            (() => {
                const cancelBtn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Cancel') || b.textContent.includes('✕'));
                if (cancelBtn) cancelBtn.click();
            })()
        """)
        time.sleep(0.5)

        cdp.eval_js("""
            (() => {
                const bellBtn = document.querySelector('button[aria-label*="Notifications"]') || document.querySelector('button:has(svg.lucide-bell)');
                if (bellBtn) bellBtn.click();
            })()
        """)
        time.sleep(1.5)
        cdp.screenshot("phase3_07_smart_notifications_bell.png")

        print("\nALL PHASE 3 SCREENSHOTS CAPTURED SUCCESSFULLY!")

    finally:
        if cdp:
            cdp.close()
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()
        try:
            shutil.rmtree(user_data_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
