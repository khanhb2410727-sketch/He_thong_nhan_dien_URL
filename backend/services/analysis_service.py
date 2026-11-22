"""Thu thập thông tin bổ sung về URL/domain (DNS, SSL/TLS, WHOIS)."""

from __future__ import annotations

import logging
import socket
import ssl
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Any

from backend.services.url_service import URLService

logger = logging.getLogger(__name__)


def _first(value: Any) -> Any:
    if isinstance(value, (list, tuple, set)):
        for item in value:
            if item is not None:
                return item
        return None
    return value


def _to_iso(value: Any) -> str | None:
    value = _first(value)
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


class AnalysisService:
    def __init__(self, timeout: int = 5) -> None:
        self.timeout = timeout
        self.url_service = URLService(timeout=timeout)
        self._pool = ThreadPoolExecutor(max_workers=4)

    # ------------------------------------------------------------------
    # DNS
    # ------------------------------------------------------------------
    def dns_lookup(self, hostname: str) -> dict[str, Any]:
        try:
            infos = socket.getaddrinfo(hostname, None)
        except (socket.gaierror, OSError) as exc:
            return {
                "resolved": False,
                "ipv4": [],
                "ipv6": [],
                "error": str(exc),
            }

        ipv4: set[str] = set()
        ipv6: set[str] = set()

        for info in infos:
            address = info[4][0].split("%")[0]
            if ":" in address:
                ipv6.add(address)
            else:
                ipv4.add(address)

        return {
            "resolved": bool(ipv4 or ipv6),
            "ipv4": sorted(ipv4),
            "ipv6": sorted(ipv6),
            "error": None,
        }

    # ------------------------------------------------------------------
    # SSL/TLS
    # ------------------------------------------------------------------
    def _read_certificate(
        self,
        hostname: str,
        context: ssl.SSLContext,
        binary: bool = False,
    ):
        with socket.create_connection(
            (hostname, 443), timeout=self.timeout
        ) as raw_socket:
            with context.wrap_socket(
                raw_socket, server_hostname=hostname
            ) as tls_socket:
                return (
                    tls_socket.getpeercert(binary_form=binary),
                    tls_socket.cipher(),
                    tls_socket.version(),
                )

    @staticmethod
    def _default_ssl_context() -> ssl.SSLContext:
        # Trên Windows, kho chứng chỉ hệ thống đôi khi thiếu CA gốc.
        # Ưu tiên bundle certifi đi kèm requests nếu có.
        try:
            import certifi

            return ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            return ssl.create_default_context()

    def ssl_info(self, hostname: str) -> dict[str, Any]:
        verified = True
        verification_error = None
        certificate_details = True

        try:
            certificate, cipher, protocol = self._read_certificate(
                hostname, self._default_ssl_context()
            )
        except ssl.SSLCertVerificationError as exc:
            # Vẫn mở kết nối để lấy thông tin giao thức/cipher, nhưng đánh dấu
            # chứng chỉ chưa được xác thực chuỗi tin cậy.
            verified = False
            certificate_details = False
            verification_error = str(exc)
            fallback_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            fallback_context.check_hostname = False
            fallback_context.verify_mode = ssl.CERT_NONE

            try:
                raw_certificate, cipher, protocol = self._read_certificate(
                    hostname, fallback_context, binary=True
                )
            except (OSError, ssl.SSLError, ValueError) as fallback_exc:
                return {
                    "available": False,
                    "error": str(fallback_exc),
                }

            if not raw_certificate:
                return {
                    "available": False,
                    "error": "Không nhận được chứng chỉ SSL/TLS.",
                }

            certificate = {}
        except (OSError, ssl.SSLError, ValueError) as exc:
            return {
                "available": False,
                "error": str(exc),
            }

        if verified and not certificate:
            return {
                "available": False,
                "error": "Không nhận được chứng chỉ SSL/TLS.",
            }

        result: dict[str, Any] = {
            "available": True,
            "verified": verified,
            "verification_error": verification_error,
            "certificate_details_available": certificate_details,
            "protocol": protocol,
            "cipher": cipher[0] if cipher else None,
            "cipher_bits": cipher[2] if cipher and len(cipher) > 2 else None,
            "issuer": {
                key: value
                for item in certificate.get("issuer", ())
                for key, value in item
            },
            "subject": {
                key: value
                for item in certificate.get("subject", ())
                for key, value in item
            },
            "subject_alt_names": [
                value
                for key, value in certificate.get("subjectAltName", ())
                if key.lower() == "dns"
            ],
            "serial_number": certificate.get("serialNumber"),
            "version": certificate.get("version"),
            "not_before": None,
            "not_after": None,
            "days_until_expiry": None,
            "error": None,
        }

        not_before = certificate.get("notBefore")
        not_after = certificate.get("notAfter")

        try:
            if not_before:
                timestamp = ssl.cert_time_to_seconds(not_before)
                result["not_before"] = datetime.fromtimestamp(
                    timestamp, tz=timezone.utc
                ).isoformat()
            if not_after:
                timestamp = ssl.cert_time_to_seconds(not_after)
                result["not_after"] = datetime.fromtimestamp(
                    timestamp, tz=timezone.utc
                ).isoformat()
                result["days_until_expiry"] = (
                    datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    - datetime.now(timezone.utc)
                ).days
        except (ValueError, OverflowError):
            pass

        return result

    # ------------------------------------------------------------------
    # WHOIS
    # ------------------------------------------------------------------
    def whois_info(self, registered_domain: str) -> dict[str, Any]:
        try:
            import whois  # type: ignore
        except ImportError:
            return {
                "available": False,
                "error": (
                    "Chưa cài đặt python-whois. "
                    "Cài bằng: pip install python-whois"
                ),
            }

        try:
            record = whois.whois(registered_domain)
        except Exception as exc:  # thư viện whois ném nhiều loại lỗi khác nhau
            return {
                "available": False,
                "error": str(exc),
            }

        creation_date = _first(record.get("creation_date"))
        expiration_date = _first(record.get("expiration_date"))
        updated_date = _first(record.get("updated_date"))

        age_days = None
        if isinstance(creation_date, datetime):
            reference = creation_date
            if reference.tzinfo is None:
                reference = reference.replace(tzinfo=timezone.utc)
            age_days = (datetime.now(timezone.utc) - reference).days
        elif isinstance(creation_date, date):
            age_days = (datetime.now(timezone.utc).date() - creation_date).days

        name_servers = record.get("name_servers")
        if isinstance(name_servers, str):
            name_servers = [name_servers]
        elif name_servers is None:
            name_servers = []
        else:
            name_servers = sorted({str(item) for item in name_servers})

        return {
            "available": True,
            "domain_name": _first(record.get("domain_name")),
            "registrar": _first(record.get("registrar")),
            "org": _first(record.get("org")),
            "country": _first(record.get("country")),
            "creation_date": _to_iso(creation_date),
            "updated_date": _to_iso(updated_date),
            "expiration_date": _to_iso(expiration_date),
            "domain_age_days": age_days,
            "name_servers": name_servers,
            "error": None,
        }

    # ------------------------------------------------------------------
    # Tổng hợp
    # ------------------------------------------------------------------
    def _resolve_future(
        self,
        future: Future,
        label: str,
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return future.result(timeout=self.timeout + 1)
        except Exception as exc:
            logger.warning("Lỗi khi thu thập %s: %s", label, exc)
            return {**fallback, "error": str(exc)}

    def collect(self, url: str) -> dict[str, Any]:
        features = self.url_service.extract_features(url)

        hostname = features.get("hostname") or ""
        domain = features.get("domain") or ""
        suffix = features.get("suffix") or ""
        registered_domain = (
            f"{domain}.{suffix}" if domain and suffix else (hostname or domain)
        )

        warnings: list[str] = []

        redirect_keys = {
            "redirect_count",
            "final_url",
            "redirect_chain",
            "redirect_failed",
            "redirect_error",
            "network_checked",
        }
        redirect_info = {
            key: features.get(key)
            for key in redirect_keys
        }

        if features.get("redirect_failed") == 1:
            warnings.append(
                "Không thể kiểm tra chuyển hướng của URL: "
                f"{features.get('redirect_error')}"
            )
        if features.get("network_checked") is False:
            warnings.append(
                "Hostname không phải địa chỉ công khai nên hệ thống không "
                "thực hiện request mạng tới URL này."
            )

        is_public = self.url_service.is_public_hostname(hostname)

        if is_public:
            dns_future = self._pool.submit(self.dns_lookup, hostname)
            ssl_future = self._pool.submit(self.ssl_info, hostname)
            whois_future = self._pool.submit(
                self.whois_info, registered_domain
            )

            dns_result = self._resolve_future(
                dns_future,
                "DNS",
                {"resolved": False, "ipv4": [], "ipv6": []},
            )
            ssl_result = self._resolve_future(
                ssl_future,
                "SSL/TLS",
                {"available": False},
            )
            whois_result = self._resolve_future(
                whois_future,
                "WHOIS",
                {"available": False},
            )
        else:
            reason = "Hostname không phải địa chỉ công khai."
            dns_result = {
                "resolved": False,
                "ipv4": [],
                "ipv6": [],
                "error": reason,
            }
            ssl_result = {"available": False, "error": reason}
            whois_result = {"available": False, "error": reason}

        if dns_result.get("error"):
            warnings.append(f"DNS: {dns_result['error']}")
        if ssl_result.get("error"):
            warnings.append(f"SSL/TLS: {ssl_result['error']}")
        if ssl_result.get("verification_error"):
            warnings.append(
                "SSL/TLS: chứng chỉ chưa được xác thực đầy đủ "
                f"({ssl_result['verification_error']})."
            )
        if whois_result.get("error"):
            warnings.append(f"WHOIS: {whois_result['error']}")

        url_info = {
            key: value
            for key, value in features.items()
            if key not in redirect_keys
        }
        url_info["registered_domain"] = registered_domain

        return {
            "url_info": url_info,
            "redirect_info": redirect_info,
            "domain_info": {
                "registered_domain": registered_domain,
                "tld": suffix or None,
                "dns": dns_result,
                "ssl": ssl_result,
                "whois": whois_result,
            },
            "warnings": warnings,
        }


analysis_service = AnalysisService()
