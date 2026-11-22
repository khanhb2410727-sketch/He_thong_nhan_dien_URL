"""Trích xuất các tín hiệu Symbolic có khả năng giải thích từ URL.
Các luật chỉ mang tính chất heuristic, không phải kết luận chắc chắn về mã độc.
Module chỉ phân tích chuỗi URL, không truy cập hoặc mở URL.
"""
from __future__ import annotations
import re
from urllib.parse import parse_qs, unquote, urlsplit
from .preprocessing import _normalise_url, _is_ip, _registered_domain

#Danh sách tên 12 luật theo thứ tự cố định, dùng để tạo vector đặc trưng
RULE_NAMES = [
    "ip_address",
    "punycode",
    "excessive_subdomains",
    "long_url",
    "special_character_anomaly",
    "suspicious_keywords",
    "brand_impersonation",
    "suspicious_extension",
    "high_digit_ratio",
    "encoding_anomaly",
    "excessive_hyphens",
    "suspicious_redirect",
]

#Tập hợp các từ khóa thường xuất hiện trong URL liên quan đến đăng nhập, xác thực và thanh toán
SUSPICIOUS_KEYWORDS = {
    "login", "log-in", "signin", "sign-in", "verify", "verification",
    "account", "password", "passwd", "credential", "authentication",
    "confirm", "update", "secure", "banking", "wallet", "recover",
    "reset", "webscr", "payment", "billing",
}

#Ánh xạ tên thương hiệu với các domain hợp pháp đã biết
#Chỉ bổ sung thương hiệu và domain khi có căn cứ xác thực
BRAND_DOMAINS = {
    "paypal": {"paypal.com"},
    "google": {"google.com"},
    "facebook": {"facebook.com"},
    "instagram": {"instagram.com"},
    "microsoft": {"microsoft.com", "live.com"},
    "apple": {"apple.com"},
    "amazon": {"amazon.com", "amazon.co.uk"},
    "netflix": {"netflix.com"},
    "linkedin": {"linkedin.com"},
    "dropbox": {"dropbox.com"},
    "outlook": {"outlook.com", "live.com"},
}

#Các phần mở rộng file có khả năng chứa hoặc thực thi mã
SUSPICIOUS_EXTENSIONS = {
    ".exe", ".scr", ".bat", ".cmd", ".msi", ".js", ".vbs",
    ".ps1", ".jar", ".hta", ".apk",
}


#Các tên tham số thường được sử dụng để chuyển hướng URL sang một địa chỉ khác
REDIRECT_KEYS = {
    "url", "u", "target", "redirect", "redirect_url", "redir",
    "return", "return_to", "continue", "dest", "destination", "next",
}


#Tập hợp các ký tự đặc biệt được sử dụng để phát hiện URL có dấu hiệu bất thường
SPECIAL_CHARS = set("@!$'()*+,;=")


#Trích xuất các tín hiệu Symbolic từ URL theo thứ tự luật đã định nghĩa
class URLRuleExtractor:
    def __init__(
        self,
        suspicious_keywords=None,
        brand_domains=None,
        suspicious_extensions=None,
        max_url_length: int = 100,
        max_subdomains: int = 2,
        max_digit_ratio: float = 0.30,
        max_encoding_ratio: float = 0.10,
        max_hyphens: int = 2,
    ):
        #Khởi tạo tập từ khóa đáng ngờ, sử dụng giá trị mặc định nếu không được truyền vào
        self.suspicious_keywords = set(suspicious_keywords or SUSPICIOUS_KEYWORDS)

        #Khởi tạo danh sách thương hiệu và domain hợp pháp tương ứng
        self.brand_domains = brand_domains or BRAND_DOMAINS

        #Khởi tạo tập phần mở rộng file đáng ngờ
        self.suspicious_extensions = set(
            suspicious_extensions or SUSPICIOUS_EXTENSIONS
        )

        #Thiết lập ngưỡng độ dài URL tối đa
        self.max_url_length = max_url_length

        #Thiết lập số lượng subdomain tối đa được xem là bình thường
        self.max_subdomains = max_subdomains

        #Thiết lập tỷ lệ chữ số tối đa trong hostname
        self.max_digit_ratio = max_digit_ratio

        #Thiết lập tỷ lệ ký tự mã hóa tối đa trong URL
        self.max_encoding_ratio = max_encoding_ratio

        #Thiết lập số lượng dấu gạch ngang tối đa trong hostname
        self.max_hyphens = max_hyphens

    #Phân tích một URL và trả về các tín hiệu luật cùng thông tin đặc trưng
    def extract(self, url: str) -> dict:

        #Lưu URL gốc sau khi loại bỏ khoảng trắng ở hai đầu
        raw = str(url or "").strip()

        #Chuẩn hóa URL để thuận tiện cho quá trình phân tích
        normalised = _normalise_url(raw)

        #Phân tách URL thành hostname, đường dẫn và tham số truy vấn
        try:
            parsed = urlsplit(normalised)
            #hostname
            host = (parsed.hostname or "").lower().strip(".")
            #đường dẫn
            path = parsed.path or ""
            #tham số truy vấn
            query = parsed.query or ""
        except ValueError:
            #Gán chuỗi rỗng cho các thành phần nếu URL không thể phân tích
            host, path, query = "", "", ""

        #Giải mã các ký tự percent-encoding và chuyển URL về chữ thường
        decoded = unquote(normalised).lower()

        #Tách hostname thành các thành phần domain
        host_parts = [part for part in host.split(".") if part]

        #Tính số lượng subdomain bằng tổng thành phần trừ domain chính và hậu tố
        subdomain_count = max(0, len(host_parts) - 2)

        #Loại bỏ các ký tự không phải chữ cái hoặc chữ số trong hostname
        host_alnum = re.sub(r"[^a-z0-9]", "", host)

        #Tính tỷ lệ chữ số trên tổng số ký tự hostname
        digit_ratio = (
            sum(ch.isdigit() for ch in host) / len(host)
            if host else 0.0
        )

        #Tìm các chuỗi percent-encoding hợp lệ có dạng %XX trong URL gốc
        encoded_matches = re.findall(r"%[0-9a-fA-F]{2}", raw)

        #Tính tỷ lệ số chuỗi mã hóa trên tổng độ dài URL
        encoding_ratio = len(encoded_matches) / max(1, len(raw))

        #Ghép hostname, đường dẫn, tham số truy vấn và URL đã giải mã để kiểm tra từ khóa
        keyword_text = f"{host} {path} {query} {decoded}"

        #Tìm các từ khóa đáng ngờ xuất hiện độc lập trong nội dung URL
        #Không khớp nếu từ khóa chỉ là một phần của chuỗi chữ và số khác
        found_keywords = sorted(
            keyword for keyword in self.suspicious_keywords
            if re.search(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])",
                         keyword_text)
        )

        #Trích xuất domain đăng ký gần đúng từ hostname
        registered = _registered_domain(host)

        #Khởi tạo danh sách lưu các thương hiệu có dấu hiệu bị giả mạo
        brand_matches = []

        #Duyệt qua từng thương hiệu và các domain hợp pháp tương ứng
        for brand, legitimate_domains in self.brand_domains.items():

            #Kiểm tra tên thương hiệu có xuất hiện độc lập trong hostname hay không
            brand_in_host = re.search(
                rf"(?<![a-z0-9]){re.escape(brand)}(?![a-z0-9])", host
            ) is not None

            #Kiểm tra hostname có trùng hoặc là subdomain của domain hợp pháp hay không
            legitimate = any(
                host == domain or host.endswith("." + domain)
                for domain in legitimate_domains
            )

            #Đánh dấu thương hiệu nếu xuất hiện trong hostname nhưng domain không hợp pháp
            if brand_in_host and not legitimate:
                brand_matches.append(brand)

        #Chuyển đường dẫn về chữ thường để kiểm tra phần mở rộng file
        path_lower = path.lower()

        #Kiểm tra đường dẫn có kết thúc bằng phần mở rộng file đáng ngờ hay không
        extension_match = any(
            path_lower.endswith(ext) for ext in self.suspicious_extensions
        )

        #Phân tích các tham số truy vấn của URL thành dictionary
        try:
            #Giữ lại cả những tham số có giá trị rỗng
            query_params = parse_qs(query, keep_blank_values=True)
        except ValueError:
            #Sử dụng dictionary rỗng nếu không thể phân tích tham số
            query_params = {}

        #Biến đánh dấu URL có tham số chuyển hướng đến hostname bên ngoài
        external_redirect = False

        #Duyệt qua từng tham số truy vấn và danh sách giá trị tương ứng
        for key, values in query_params.items():

            #Bỏ qua tham số nếu tên không thuộc nhóm tham số chuyển hướng
            if key.lower() not in REDIRECT_KEYS:
                continue

            #Kiểm tra từng giá trị của tham số chuyển hướng
            for value in values:

                #Giải mã giá trị và loại bỏ khoảng trắng ở hai đầu
                candidate = unquote(value.strip())

                #Chỉ kiểm tra các giá trị có dạng URL HTTP, HTTPS hoặc URL tương đối bắt đầu bằng //
                if candidate.startswith(("http://", "https://", "//")):
                    try:
                        #Phân tích hostname đích của URL chuyển hướng
                        target_host = (urlsplit(
                            candidate if "://" in candidate
                            else "http:" + candidate
                        ).hostname or "").lower()

                        #Đánh dấu nếu hostname đích khác hostname ban đầu
                        if target_host and target_host != host:
                            external_redirect = True

                    except ValueError:
                        #Bỏ qua giá trị chuyển hướng không thể phân tích
                        pass

        #Đếm tổng số lần xuất hiện của các ký tự đặc biệt trong URL gốc
        special_count = sum(raw.count(char) for char in SPECIAL_CHARS)

        #Xây dựng dictionary chứa kết quả kích hoạt của 12 luật Symbolic
        #Mỗi luật trả về 1.0 nếu được kích hoạt và 0.0 nếu không được kích hoạt
        signals = {
            #Hostname sử dụng địa chỉ IP thay vì tên miền
            "ip_address": float(_is_ip(host)),

            #Hostname chứa nhãn punycode có tiền tố xn--
            "punycode": float("xn--" in host),

            #Số lượng subdomain vượt quá ngưỡng cho phép
            "excessive_subdomains": float(subdomain_count > self.max_subdomains),

            #Độ dài URL vượt quá ngưỡng quy định
            "long_url": float(len(raw) > self.max_url_length),

            #URL chứa ít nhất 4 ký tự đặc biệt hoặc có ký tự @
            "special_character_anomaly": float(special_count >= 4 or "@" in raw),

            #URL chứa ít nhất một từ khóa đáng ngờ
            "suspicious_keywords": float(bool(found_keywords)),

            #Tên thương hiệu xuất hiện trong hostname không thuộc domain hợp pháp
            "brand_impersonation": float(bool(brand_matches)),

            #Đường dẫn kết thúc bằng phần mở rộng file đáng ngờ
            "suspicious_extension": float(extension_match),

            #Tỷ lệ chữ số trong hostname vượt quá ngưỡng quy định
            "high_digit_ratio": float(digit_ratio > self.max_digit_ratio),

            #Tỷ lệ ký tự percent-encoding vượt quá ngưỡng quy định
            "encoding_anomaly": float(encoding_ratio > self.max_encoding_ratio),

            #Số lượng dấu gạch ngang trong hostname vượt quá ngưỡng quy định
            "excessive_hyphens": float(host.count("-") > self.max_hyphens),

            #Tham số chuyển hướng trỏ đến một hostname khác
            "suspicious_redirect": float(external_redirect),
        }

        #Lưu các đặc trưng số và thông tin chi tiết phục vụ phân tích, giải thích kết quả
        metadata = {
            "host": host,
            "registered_domain": registered,
            "url_length": len(raw),
            "subdomain_count": subdomain_count,
            "digit_ratio": digit_ratio,
            "encoding_ratio": encoding_ratio,
            "special_character_count": special_count,
            "suspicious_keywords_found": found_keywords,
            "brand_matches": brand_matches,
            "is_ip": _is_ip(host),
            "has_punycode": "xn--" in host,
        }

        #Trả về dictionary chứa các tín hiệu luật và metadata
        return {"signals": signals, "metadata": metadata}

    #Chuyển một URL thành vector đặc trưng theo thứ tự cố định của RULE_NAMES
    def transform_one(self, url: str) -> list[float]:

        #Trích xuất các tín hiệu Symbolic từ URL
        result = self.extract(url)

        #Lấy giá trị kích hoạt của từng luật theo đúng thứ tự đã định nghĩa
        return [result["signals"][name] for name in RULE_NAMES]

    #Chuyển danh sách URL thành ma trận vector đặc trưng Symbolic
    def transform(self, urls) -> list[list[float]]:

        #Trích xuất vector đặc trưng cho từng URL trong danh sách
        #Kết quả có dạng [N, R], với N là số URL và R là số luật
        return [self.transform_one(url) for url in urls]
