"""Trích xuất đặc trưng URL và thông tin domain cơ bản."""

import ipaddress
import math
import re
import socket
import urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import requests
import tldextract

_DNS_CHECK_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _is_public_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%")[0])
    except ValueError:
        return False
    return address.is_global


class URLService:

    SHORTENERS = {
        "bit.ly", "tinyurl.com", "t.co",
        "ow.ly", "is.gd", "cutt.ly",
        "rb.gy", "rebrand.ly", "shorturl.at"
    }

    SUSPICIOUS_TLDS = {
        "xyz", "top", "click", "work",
        "buzz", "tk", "ml", "ga", "cf"
    }

    SUSPICIOUS_EXTENSIONS = {
        ".exe", ".scr", ".bat", ".cmd",
        ".msi", ".apk", ".vbs", ".js",
        ".ps1", ".jar"
    }

    SPECIAL_CHARS = set("@!$'()*+,;=")

    def __init__(self, timeout=5):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

    # 1. Chuẩn hóa URL
    def normalize_url(self, url):
        url = str(url).strip()

        if not url:
            return None

        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
            url = "https://" + url

        return url

    # 2. Kiểm tra URL hợp lệ
    def validate_url(self, url):
        if not url or any(ch.isspace() for ch in url):
            return False

        try:
            parsed = urllib.parse.urlparse(url)

            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.hostname or not parsed.netloc:
                return False
            if parsed.username is not None or parsed.password is not None:
                return False

            # Truy cập thuộc tính port để phát hiện port không hợp lệ
            _ = parsed.port

            hostname = parsed.hostname.rstrip(".")

            if not hostname or len(hostname) > 253:
                return False

            try:
                ipaddress.ip_address(hostname.split("%")[0])
                return True
            except ValueError:
                pass

            # Chuyển tên miền quốc tế sang dạng ASCII (punycode) để kiểm tra
            try:
                ascii_hostname = hostname.encode("idna").decode("ascii")
            except UnicodeError:
                return False

            if "." not in ascii_hostname:
                return False
            if not re.fullmatch(r"[a-z0-9.-]+", ascii_hostname):
                return False

            labels = ascii_hostname.split(".")
            return all(
                label
                and len(label) <= 63
                and not label.startswith("-")
                and not label.endswith("-")
                for label in labels
            )

        except ValueError:
            return False

    # 3. Kiểm tra hostname có an toàn để thực hiện request mạng hay không.
    # Tránh trường hợp backend bị dùng để truy cập các địa chỉ nội bộ (SSRF).
    def is_public_hostname(self, hostname):
        if not hostname:
            return False

        host = hostname.strip("[]").lower().rstrip(".")

        if host in {"localhost", "localhost.localdomain"}:
            return False

        if host.endswith((".localhost", ".local", ".internal", ".home", ".lan")):
            return False

        try:
            return ipaddress.ip_address(host.split("%")[0]).is_global
        except ValueError:
            pass

        try:
            future = _DNS_CHECK_EXECUTOR.submit(
                socket.getaddrinfo, host, None, 0, socket.SOCK_STREAM
            )
            infos = future.result(timeout=2)
        except Exception:
            return False

        addresses = {
            info[4][0]
            for info in infos
            if info and info[4]
        }

        return bool(addresses) and all(_is_public_ip(ip) for ip in addresses)

    # 4. Lấy thông tin domain
    def get_domain_info(self, url):
        parsed = urllib.parse.urlparse(url)

        ext = tldextract.extract(url)

        return {
            "scheme": parsed.scheme,
            "hostname": parsed.hostname,
            "domain": ext.domain,
            "suffix": ext.suffix,
            "subdomain": ext.subdomain,
            "subdomain_depth": (
                len(ext.subdomain.split("."))
                if ext.subdomain else 0
            )
        }

    # 5. Kiểm tra chuyển hướng
    def check_redirect(self, url):
        try:
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                stream=True
            )

            result = {
                "redirect_count": len(response.history),
                "final_url": response.url,
                "redirect_chain": [
                    r.url for r in response.history
                ] + [response.url],
                "redirect_failed": 0,
                "redirect_error": None,
                "network_checked": True,
            }

            response.close()
            return result

        except requests.RequestException as exc:
            return {
                "redirect_count": None,
                "final_url": None,
                "redirect_chain": [],
                "redirect_failed": 1,
                "redirect_error": str(exc),
                "network_checked": True,
            }

    # 6. Tính URL entropy
    def calculate_entropy(self, url):
        if not url:
            return 0

        frequency = Counter(url)
        length = len(url)

        return -sum(
            (count / length) * math.log2(count / length)
            for count in frequency.values()
        )

    # 7. Trích xuất toàn bộ đặc trưng
    def extract_features(self, url):
        url = self.normalize_url(url)

        if not self.validate_url(url):
            raise ValueError("URL không hợp lệ.")

        parsed = urllib.parse.urlparse(url)
        ext = tldextract.extract(url)

        domain_info = self.get_domain_info(url)

        hostname = (parsed.hostname or "").lower()
        path = parsed.path or ""
        query = parsed.query or ""

        # Chỉ thực hiện request mạng khi hostname trỏ ra Internet công khai
        if self.is_public_hostname(hostname):
            redirect_info = self.check_redirect(url)
        else:
            redirect_info = {
                "redirect_count": None,
                "final_url": None,
                "redirect_chain": [],
                "redirect_failed": 2,
                "redirect_error": (
                    "Không thực hiện request vì hostname không phải địa chỉ "
                    "công khai (bảo vệ SSRF)."
                ),
                "network_checked": False,
            }

        # Punycode
        has_punycode = "xn--" in hostname

        # Suspicious TLD
        has_suspicious_tld = (
            ext.suffix.split(".")[-1].lower()
            in self.SUSPICIOUS_TLDS
        )

        # Shortened URL
        has_shortened_url = hostname in self.SHORTENERS

        # URL Encoding
        url_encoding_count = url.count("%")

        # File extension
        path_lower = path.lower()

        has_suspicious_file_extension = any(
            path_lower.endswith(e)
            for e in self.SUSPICIOUS_EXTENSIONS
        )

        # Các đặc trưng cấu trúc bổ sung
        try:
            is_ip_host = ipaddress.ip_address(hostname.split("%")[0]) is not None
        except ValueError:
            is_ip_host = False

        digit_count = sum(ch.isdigit() for ch in url)
        special_count = sum(url.count(ch) for ch in self.SPECIAL_CHARS)

        return {
            "url": url,

            # Redirect
            **redirect_info,

            # URL features
            "url_encoding_count": url_encoding_count,
            "url_entropy": self.calculate_entropy(url),
            "url_length": len(url),
            "hostname_length": len(hostname),
            "path_length": len(path),
            "query_length": len(query),
            "count_dot": url.count("."),
            "count_hyphen": url.count("-"),
            "count_digit": digit_count,
            "count_special": special_count,
            "digit_ratio": (
                digit_count / len(url) if url else 0.0
            ),
            "is_https": int(parsed.scheme == "https"),
            "has_ip_host": int(is_ip_host),
            "path_extension": (
                path_lower.rsplit("/", 1)[-1].rsplit(".", 1)[-1]
                if "." in path_lower.rsplit("/", 1)[-1]
                else None
            ),

            # Domain features
            "has_punycode": int(has_punycode),
            "has_suspicious_tld": int(has_suspicious_tld),
            "has_shortened_url": int(has_shortened_url),
            "subdomain_depth": domain_info["subdomain_depth"],
            "has_suspicious_file_extension":
                int(has_suspicious_file_extension),

            # Domain information
            **domain_info
        }

    # 8. Trích xuất nhiều URL
    def extract_batch_features(self, urls):
        results = []

        for url in urls:
            try:
                features = self.extract_features(url)
                results.append(features)

            except (ValueError, TypeError) as e:
                results.append({
                    "url": url,
                    "error": str(e)
                })

        return results

    # 9. Đóng session
    def close(self):
        self.session.close()
