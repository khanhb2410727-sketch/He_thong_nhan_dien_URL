"""Knowledge base: rule descriptions, confidence and initial weights."""

from dataclasses import dataclass

#Cấu trúc dữ liệu 1 rule
@dataclass(frozen=True)
class RuleKnowledge:
    name: str
    confidence: float
    weight: float
    severity: str = "medium"



#Quản lý toàn bộ tri thức
class KnowledgeBase:
    #Định nghĩa các luật phát hiện URL bất thường
    def __init__(self):
        entries = [
            # Phát hiện URL sử dụng địa chỉ IP thay vì tên miền thông thường, có thể nhằm che giấu máy chủ đích.
            RuleKnowledge("ip_address", 0.75, 0.80, "high"),
            # Phát hiện tên miền sử dụng ký tự Punycode (xn--), có thể giả mạo tên miền hợp pháp bằng ký tự Unicode tương tự.
            RuleKnowledge("punycode", 0.80, 0.85, "high"),
            # Phát hiện URL có quá nhiều cấp tên miền phụ (subdomain), có thể được sử dụng để tạo tên miền giả mạo hoặc gây nhầm lẫn.
            RuleKnowledge("excessive_subdomains", 0.65, 0.55, "medium"),
            # Phát hiện URL có độ dài bất thường, có thể được sử dụng để che giấu thông tin hoặc khiến người dùng khó nhận biết địa chỉ thực.
            RuleKnowledge("long_url", 0.30, 0.15, "low"),
            # Phát hiện các ký tự đặc biệt xuất hiện bất thường trong URL, có thể nhằm đánh lừa người dùng hoặc che giấu đường dẫn thực.
            RuleKnowledge("special_character_anomaly", 0.70, 0.65, "medium"),
            # Phát hiện các từ khóa đáng ngờ trong URL như login, verify, secure, account, nhằm dụ người dùng truy cập trang giả mạo.
            RuleKnowledge("suspicious_keywords", 0.45, 0.25, "low"),
            # Phát hiện tên miền hoặc URL có dấu hiệu giả mạo thương hiệu nổi tiếng nhằm đánh cắp thông tin người dùng.
            RuleKnowledge("brand_impersonation", 0.98, 1.00, "high"),
            # Phát hiện URL sử dụng phần mở rộng tệp đáng ngờ như .exe, .scr, .bat, có thể dẫn đến việc tải xuống mã độc.
            RuleKnowledge("suspicious_extension", 0.75, 0.70, "high"),
            # Phát hiện tỷ lệ chữ số trong URL cao bất thường, có thể là dấu hiệu của tên miền được tạo tự động hoặc đáng ngờ.
            RuleKnowledge("high_digit_ratio", 0.55, 0.35, "medium"),
            # Phát hiện các dấu hiệu mã hóa bất thường trong URL như chuỗi percent-encoding hoặc ký tự mã hóa nhiều lần nhằm che giấu nội dung thực.
            RuleKnowledge("encoding_anomaly", 0.80, 0.80, "high"),
            # Phát hiện URL chứa quá nhiều dấu gạch ngang (-), có thể là dấu hiệu của tên miền giả mạo hoặc được tạo nhằm bắt chước thương hiệu.
            RuleKnowledge("excessive_hyphens", 0.50, 0.30, "low"),
            # Phát hiện URL có hành vi chuyển hướng đáng ngờ, có thể đưa người dùng đến trang web lừa đảo hoặc trang chứa mã độc.
            RuleKnowledge("suspicious_redirect", 0.90, 0.90, "high")
        ]
        #Lưu luật vào dictionary
        # self._rules = {
        #     "ip_address": RuleKnowledge(...),
        #     "punycode": RuleKnowledge(...)
        # }
        self._rules = {item.name: item for item in entries}

    #Lấy thông tin luật
    def get(self, rule_name: str) -> RuleKnowledge:
        return self._rules[rule_name]

    #Lấy danh sách toàn bộ các luật
    def all(self) -> list[RuleKnowledge]:
        return list(self._rules.values())

    #Chuyển luật thành 1 vector confidence
    def confidence_vector(self, rule_names: list[str]) -> list[float]:
        return [self.get(name).confidence for name in rule_names]

    #Lấy 1 vector weight
    def weight_vector(self, rule_names: list[str]) -> list[float]:
        return [self.get(name).weight for name in rule_names]
