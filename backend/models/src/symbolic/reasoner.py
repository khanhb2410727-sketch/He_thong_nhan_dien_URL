"""Tổng hợp các luật có khả năng giải thích cho bài toán phân loại URL."""

from dataclasses import dataclass
from .rules import URLRuleExtractor, RULE_NAMES
from .knowlegde_base import KnowledgeBase
from .constraints import SymbolicConstraints


#Cấu trúc dữ liệu lưu kết quả suy luận Symbolic cho một URL
@dataclass
class ReasoningResult:
    score: float                   #Điểm đánh giá mức độ đáng ngờ của URL
    predicted_label: int           #Nhãn dự đoán: 1 - Phishing, 0 - Legitimate
    active_rules: list[dict]       #Danh sách các luật được kích hoạt
    signals: dict                  #Kết quả kích hoạt của toàn bộ các luật
    metadata: dict                 #Thông tin đặc trưng được trích xuất từ URL
    feature_vector: list[float]    #Vector đặc trưng biểu diễn trạng thái kích hoạt của các luật


#Thực hiện suy luận Symbolic dựa trên các luật và tri thức đã định nghĩa
class SymbolicReasoner:
    def __init__(
        self,
        extractor=None,
        knowledge_base=None,
        constraints=None,
    ):
        #Khởi tạo bộ trích xuất đặc trưng và kiểm tra các luật trên URL
        self.extractor = extractor or URLRuleExtractor()

        #Khởi tạo Knowledge Base chứa confidence, weight và metadata của các luật
        self.knowledge_base = knowledge_base or KnowledgeBase()

        #Khởi tạo và kiểm tra tính hợp lệ của các tham số cấu hình Symbolic
        self.constraints = (constraints or SymbolicConstraints()).validate()

    #Phân tích URL và thực hiện suy luận dựa trên các luật Symbolic
    def reason(self, url: str) -> ReasoningResult:

        #Trích xuất các tín hiệu luật và metadata từ URL đầu vào
        extracted = self.extractor.extract(url)
        signals = extracted["signals"]

        #Khởi tạo danh sách lưu các luật được kích hoạt
        active_rules = []

        #Tử số dùng để tính điểm suy luận Symbolic
        numerator = 0.0

        #Mẫu số dùng để chuẩn hóa điểm suy luận theo tổng trọng số
        denominator = 0.0

        #Duyệt qua toàn bộ các luật đã được định nghĩa
        for name in RULE_NAMES:

            #Bỏ qua luật nếu tín hiệu tương ứng không được kích hoạt
            if not signals[name]:
                continue

            #Lấy thông tin confidence, weight và metadata của luật từ Knowledge Base
            knowledge = self.knowledge_base.get(name)

            #Tính mức đóng góp của luật dựa trên confidence và weight
            #Nếu tắt confidence weighting thì chỉ sử dụng weight
            contribution = (
                knowledge.confidence * knowledge.weight
                if self.constraints.use_confidence_weighting
                else knowledge.weight
            )

            #Cộng mức đóng góp của luật vào tử số
            numerator += contribution

            #Cộng trọng số của luật vào mẫu số để chuẩn hóa điểm
            denominator += knowledge.weight

            #Lưu thông tin chi tiết của luật được kích hoạt để phục vụ giải thích kết quả
            active_rules.append({
                "name": name,
                "confidence": knowledge.confidence,
                "weight": knowledge.weight,
                "severity": knowledge.severity,
            })

        #Tính điểm suy luận bằng tỷ lệ giữa tổng đóng góp và tổng trọng số
        #Nếu không có luật nào được kích hoạt thì điểm suy luận bằng 0
        score = numerator / denominator if denominator else 0.0

        #Kiểm tra số lượng luật được kích hoạt có đạt ngưỡng tối thiểu hay không
        enough_rules = len(active_rules) >= self.constraints.min_active_rules

        #Dự đoán URL có dấu hiệu độc hại nếu đủ số luật và đạt ngưỡng điểm quy định
        #1: Phishing, 0: Chưa đủ bằng chứng từ Symbolic để cảnh báo
        predicted = int(
            enough_rules and score >= self.constraints.malicious_score_threshold
        )

        #Đóng gói toàn bộ kết quả suy luận thành đối tượng ReasoningResult
        return ReasoningResult(
            score=score,
            predicted_label=predicted,
            active_rules=active_rules,
            signals=signals,
            metadata=extracted["metadata"],
            feature_vector=[signals[name] for name in RULE_NAMES],
        )

    #Chuyển danh sách URL thành ma trận đặc trưng luật để sử dụng trong Dataset
    def transform(self, urls):
        #Mỗi URL được chuyển thành một vector biểu diễn trạng thái kích hoạt của các luật
        #Kết quả có dạng [N, R], với N là số URL và R là số luật
        return [self.extractor.transform_one(url) for url in urls]
