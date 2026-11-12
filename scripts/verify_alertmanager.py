"""Exercise Alertmanager routing against an isolated loopback webhook."""

import argparse
import json
import socket
import subprocess
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import URLError
from urllib.request import Request, urlopen


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.notifications.put((self.path, payload))
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def config(webhook_port):
    receivers = ("unrouted", "page", "ticket")
    return {
        "route": {
            "receiver": "unrouted",
            "group_by": ["service", "severity"],
            "group_wait": "2s",
            "group_interval": "10s",
            "repeat_interval": "1h",
            "routes": [
                {"receiver": severity, "matchers": [f'severity="{severity}"']}
                for severity in receivers[1:]
            ],
        },
        "receivers": [
            {"name": name, "webhook_configs": [
                {"url": f"http://127.0.0.1:{webhook_port}/{name}", "send_resolved": False}
            ]}
            for name in receivers
        ],
        "inhibit_rules": [{
            "source_matchers": ['severity="page"'],
            "target_matchers": ['severity="ticket"'],
            "equal": ["service"],
        }],
    }


def unused_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def fetch(url, data=None):
    request = Request(url, data=data, headers={"Content-Type": "application/json"})
    # The drill constructs URLs on loopback.
    with urlopen(request, timeout=2) as response:  # nosec B310
        return response.read()


def await_ready(base, process):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Alertmanager exited before becoming ready")
        try:
            fetch(f"{base}/-/ready")
            return
        except URLError:
            time.sleep(0.1)
    raise RuntimeError("Alertmanager did not become ready")


def send_fixtures(base):
    names = {"page": "RequestBudgetFastBurn", "ticket": "RequestBudgetSlowBurn"}
    started = datetime.now(timezone.utc)
    alerts = [
        {
            "labels": {"alertname": names[severity], "service": service, "severity": severity},
            "startsAt": started.isoformat(),
            "endsAt": (started + timedelta(minutes=5)).isoformat(),
        }
        for service, severity in (("checkout", "page"), ("checkout", "ticket"), ("catalog", "ticket"))
    ]
    fetch(f"{base}/api/v2/alerts", json.dumps(alerts).encode())


def verify_delivery(base, notifications):
    expected = {("/page", "checkout", "page"), ("/ticket", "catalog", "ticket")}
    received = set()
    for _ in expected:
        path, payload = notifications.get(timeout=10)
        for alert in payload["alerts"]:
            labels = alert["labels"]
            received.add((path, labels["service"], labels["severity"]))
    if received != expected:
        raise AssertionError(f"Unexpected webhook deliveries: {sorted(received)}")

    alerts = json.loads(fetch(f"{base}/api/v2/alerts"))
    muted = [
        alert for alert in alerts
        if alert["labels"].get("service") == "checkout" and alert["labels"].get("severity") == "ticket"
    ]
    if len(muted) != 1 or muted[0]["status"]["state"] != "suppressed" or not muted[0]["status"]["inhibitedBy"]:
        raise AssertionError("Expected the checkout ticket to be inhibited by the checkout page")
    print("PASS: checkout page delivered to page receiver")
    print("PASS: checkout ticket inhibited by the checkout page")
    print("PASS: catalog ticket delivered to ticket receiver")


def run(binary):
    with TemporaryDirectory() as directory, ThreadingHTTPServer(("127.0.0.1", 0), WebhookHandler) as webhook:
        webhook.notifications = Queue()
        receiver = Thread(target=webhook.serve_forever, daemon=True)
        receiver.start()
        state = Path(directory)
        settings = state / "alertmanager.yml"
        settings.write_text(json.dumps(config(webhook.server_port)), encoding="utf-8")
        port = unused_port()
        base = f"http://127.0.0.1:{port}"
        command = [
            binary, f"--config.file={settings}", f"--storage.path={state / 'data'}",
            f"--web.listen-address=127.0.0.1:{port}", "--cluster.listen-address=",
        ]
        try:
            with (state / "alertmanager.log").open("w+", encoding="utf-8") as log, subprocess.Popen(
                command, stdout=log, stderr=subprocess.STDOUT
            ) as process:
                try:
                    await_ready(base, process)
                    send_fixtures(base)
                    verify_delivery(base, webhook.notifications)
                except Exception:
                    log.seek(0)
                    print(log.read())
                    raise
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
        finally:
            webhook.shutdown()
            receiver.join()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alertmanager", default="alertmanager")
    run(parser.parse_args().alertmanager)
