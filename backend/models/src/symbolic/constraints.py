"""Configuration and validation for symbolic reasoning."""
from dataclasses import dataclass

# Định nghĩa SymbolicConstraints
@dataclass
class SymbolicConstraints:
    # confidence tối thiểu để một luật logic được phép tham gia tính toán Logic Loss
    min_loss_confidence: float = 0.75

    # gưỡng điểm suy luận logic để xác định một URL có dấu hiệu độc hại 
    # dựa trên các luật Symbolic.
    malicious_score_threshold: float = 0.60

    # Đây là số lượng luật tối thiểu phải được kích hoạt 
    # để hệ thống đưa ra cảnh báo dựa trên Symbolic.
    min_active_rules: int = 1

    # Tham số này xác định có sử dụng confidence để 
    # điều chỉnh mức đóng góp của từng luật vào điểm Symbolic hay không.
    use_confidence_weighting: bool = True

    def validate(self):
        if not 0.0 <= self.min_loss_confidence <= 1.0:
            raise ValueError("min_loss_confidence must be in [0, 1].")
        if not 0.0 <= self.malicious_score_threshold <= 1.0:
            raise ValueError("malicious_score_threshold must be in [0, 1].")
        if self.min_active_rules < 1:
            raise ValueError("min_active_rules must be >= 1.")
        return self
