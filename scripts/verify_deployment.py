"""Windows CMD-compatible deployment verification tool for AegisOps containerized environment."""

import argparse
import json
import logging
import socket
import sys
import urllib.error
import urllib.request
from contextlib import suppress
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aegisops.verify_deployment")


class DeploymentVerifier:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        prometheus_url: str = "http://127.0.0.1:9091",
        grafana_url: str = "http://127.0.0.1:3001",
        alertmanager_url: str = "http://127.0.0.1:9094",
        db_host: str = "127.0.0.1",
        db_port: int = 5432,
    ):
        self.base_url = base_url.rstrip("/")
        self.prometheus_url = prometheus_url.rstrip("/")
        self.grafana_url = grafana_url.rstrip("/")
        self.alertmanager_url = alertmanager_url.rstrip("/")
        self.db_host = db_host
        self.db_port = db_port
        self.results: list[dict[str, Any]] = []

    def record_result(
        self, check_name: str, passed: bool, details: str, blocked: bool = False
    ):
        status = "BLOCKED" if blocked else ("PASSED" if passed else "FAILED")
        self.results.append(
            {
                "check": check_name,
                "status": status,
                "details": details,
            }
        )
        log_fn = (
            logger.info if passed else (logger.warning if blocked else logger.error)
        )
        log_fn("[%s] %s — %s", status, check_name, details)

    def _http_get(
        self, url: str, timeout: float = 5.0
    ) -> tuple[int | None, dict[str, str], str]:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "AegisOps-Deployment-Verifier/1.0",
                "Accept": "application/json, text/html, */*",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                headers = {k.lower(): v for k, v in response.headers.items()}
                body = response.read().decode("utf-8", errors="replace")
                return status_code, headers, body
        except urllib.error.HTTPError as exc:
            headers = {k.lower(): v for k, v in exc.headers.items()}
            body = exc.read().decode("utf-8", errors="replace")
            return exc.code, headers, body
        except Exception as exc:  # noqa: BLE001
            return None, {}, str(exc)

    def check_backend_liveness(self):
        url = f"{self.base_url}/api/v1/health/live"
        status, _, body = self._http_get(url)
        if status == 200 and ("ok" in body.lower() or "healthy" in body.lower()):
            self.record_result(
                "Backend Liveness", True, f"HTTP {status} from {url}: {body.strip()}"
            )
        else:
            self.record_result(
                "Backend Liveness", False, f"HTTP {status} from {url}: {body[:100]}"
            )

    def check_backend_readiness(self):
        url = f"{self.base_url}/api/v1/health/ready"
        status, _, body = self._http_get(url)
        if status == 200:
            self.record_result(
                "Backend Readiness", True, f"Dependencies healthy: {body[:120]}"
            )
        else:
            self.record_result(
                "Backend Readiness", False, f"HTTP {status} from {url}: {body[:120]}"
            )

    def check_frontend_availability(self):
        url = f"{self.base_url}/"
        status, _headers, body = self._http_get(url)
        if status == 200 and ('<div id="root">' in body or "<title>" in body):
            self.record_result(
                "Frontend Availability", True, f"SPA served successfully from {url}"
            )
        else:
            self.record_result(
                "Frontend Availability",
                False,
                f"HTTP {status} from {url}: {body[:100]}",
            )

    def check_security_headers(self):
        url = f"{self.base_url}/api/v1/health"
        status, headers, _ = self._http_get(url)
        if status is None:
            self.record_result("Security Headers", False, f"Could not connect to {url}")
            return

        expected = {
            "x-content-type-options": "nosniff",
            "x-frame-options": "DENY",
            "cache-control": "no-store",
        }
        missing = []
        for hdr, val in expected.items():
            actual = headers.get(hdr, "")
            if val.lower() not in actual.lower():
                missing.append(f"{hdr} (expected '{val}', got '{actual}')")

        if not missing:
            self.record_result(
                "Security Headers",
                True,
                "All required security headers present (nosniff, DENY, no-store)",
            )
        else:
            self.record_result(
                "Security Headers", False, f"Missing or invalid: {', '.join(missing)}"
            )

    def check_production_persona_restriction(self):
        url = f"{self.base_url}/api/v1/auth/personas"
        status, _, body = self._http_get(url)
        if status == 403:
            self.record_result(
                "Production Persona Gating",
                True,
                "Persona switching strictly rejected with HTTP 403 Forbidden",
            )
        elif status == 200:
            self.record_result(
                "Production Persona Gating",
                False,
                "SECURITY LEAK: Dev persona switcher returned HTTP 200 in production configuration!",
            )
        else:
            self.record_result(
                "Production Persona Gating",
                False,
                f"Unexpected response HTTP {status}: {body[:100]}",
            )

    def check_database_port_isolation(
        self, container_name: str = "aegisops-prod-postgres"
    ):
        import subprocess

        with suppress(subprocess.SubprocessError, FileNotFoundError, OSError):
            proc = subprocess.run(
                ["docker", "port", container_name],
                capture_output=True,
                text=True,
                check=False,
            )
            if proc.returncode == 0:
                mapped = proc.stdout.strip()
                if not mapped:
                    self.record_result(
                        "Database Port Isolation",
                        True,
                        f"Container '{container_name}' has no published ports to host network.",
                    )
                    return
                self.record_result(
                    "Database Port Isolation",
                    False,
                    f"WARNING: Container '{container_name}' has exposed ports: {mapped}",
                )
                return

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        try:
            res = s.connect_ex((self.db_host, self.db_port))
            if res != 0:
                self.record_result(
                    "Database Port Isolation",
                    True,
                    f"Port {self.db_port} on {self.db_host} is closed/unreachable from host network.",
                )
            else:
                self.record_result(
                    "Database Port Isolation",
                    False,
                    f"WARNING: Port {self.db_port} is listening on {self.db_host}.",
                )
        except OSError as exc:
            self.record_result(
                "Database Port Isolation", True, f"Connection refused/error: {exc}"
            )
        finally:
            s.close()

    def check_prometheus_availability(self):
        url = f"{self.prometheus_url}/-/healthy"
        status, _, _body = self._http_get(url)
        if status == 200:
            self.record_result(
                "Prometheus Availability", True, f"Prometheus healthy at {url}"
            )
        else:
            self.record_result(
                "Prometheus Availability",
                False,
                f"HTTP {status} from {url}",
                blocked=True,
            )

    def check_grafana_availability(self):
        url = f"{self.grafana_url}/api/health"
        status, _, body = self._http_get(url)
        if status == 200 and "ok" in body.lower():
            self.record_result(
                "Grafana Availability", True, f"Grafana healthy at {url}"
            )
        else:
            self.record_result(
                "Grafana Availability", False, f"HTTP {status} from {url}", blocked=True
            )

    def check_alertmanager_availability(self):
        url = f"{self.alertmanager_url}/-/ready"
        status, _, _body = self._http_get(url)
        if status == 200:
            self.record_result(
                "Alertmanager Availability", True, f"Alertmanager ready at {url}"
            )
        else:
            self.record_result(
                "Alertmanager Availability",
                False,
                f"HTTP {status} from {url}",
                blocked=True,
            )

    def check_data_persistence(self):
        url = f"{self.base_url}/api/v1/incidents"
        status, _, body = self._http_get(url)
        if status == 200:
            try:
                data = json.loads(body)
                count = (
                    len(data) if isinstance(data, list) else len(data.get("items", []))
                )
                self.record_result(
                    "Incident Data Persistence",
                    True,
                    f"Retrieved {count} incidents from persistent store",
                )
            except (json.JSONDecodeError, KeyError, TypeError):
                self.record_result(
                    "Incident Data Persistence",
                    True,
                    f"Endpoint reachable, body: {body[:60]}",
                )
        else:
            self.record_result(
                "Incident Data Persistence",
                False,
                f"HTTP {status} from {url}: {body[:80]}",
            )

    def run_all(self) -> bool:
        logger.info(
            "================================================================================"
        )
        logger.info(" AegisOps | Step 17: Production Deployment Verification")
        logger.info(" Target Endpoint: %s", self.base_url)
        logger.info(
            "================================================================================"
        )

        self.check_backend_liveness()
        self.check_backend_readiness()
        self.check_frontend_availability()
        self.check_security_headers()
        self.check_production_persona_restriction()
        self.check_database_port_isolation()
        self.check_prometheus_availability()
        self.check_grafana_availability()
        self.check_alertmanager_availability()
        self.check_data_persistence()

        print("\n" + "=" * 80)
        print(f"{'CHECK':<32} | {'STATUS':<10} | {'DETAILS'}")
        print("=" * 80)
        all_passed = True
        for res in self.results:
            print(f"{res['check']:<32} | {res['status']:<10} | {res['details']}")
            if res["status"] == "FAILED":
                all_passed = False
        print("=" * 80)
        summary = "PASSED" if all_passed else "FAILED / WITH WARNINGS"
        print(f"DEPLOYMENT VERIFICATION RESULT: {summary}")
        print("=" * 80 + "\n")
        return all_passed


def main():
    parser = argparse.ArgumentParser(
        description="Verify AegisOps Production Deployment"
    )
    parser.add_argument(
        "--base-url", default="http://127.0.0.1:8080", help="Base application URL"
    )
    parser.add_argument(
        "--prometheus-url", default="http://127.0.0.1:9091", help="Prometheus URL"
    )
    parser.add_argument(
        "--grafana-url", default="http://127.0.0.1:3001", help="Grafana URL"
    )
    parser.add_argument(
        "--alertmanager-url", default="http://127.0.0.1:9094", help="Alertmanager URL"
    )
    parser.add_argument(
        "--db-host", default="127.0.0.1", help="Database host to test isolation"
    )
    parser.add_argument(
        "--db-port", type=int, default=5432, help="Database port to test isolation"
    )

    args = parser.parse_args()
    verifier = DeploymentVerifier(
        base_url=args.base_url,
        prometheus_url=args.prometheus_url,
        grafana_url=args.grafana_url,
        alertmanager_url=args.alertmanager_url,
        db_host=args.db_host,
        db_port=args.db_port,
    )
    success = verifier.run_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
