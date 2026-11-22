
"""Hàm tính Symbolic Consistency Loss có trọng số theo độ tin cậy của luật."""
import torch
import torch.nn.functional as F

#Tính toán Symbolic Consistency Loss cho một batch dữ liệu
def symbolic_consistency_loss(
    malicious_prob: torch.Tensor,
    rule_features: torch.Tensor,
    rule_confidences: torch.Tensor,
    min_confidence: float = 0.75,
    margin: float = 0.70,
) -> torch.Tensor:

    #Chuyển xác suất dự đoán về tensor 1 chiều và giới hạn trong khoảng [0, 1]
    probs = malicious_prob.reshape(-1).clamp(0.0, 1.0)

    #Chuyển các đặc trưng luật về kiểu float để phục vụ tính toán
    activations = rule_features.float()

    #Kiểm tra kích thước tensor đặc trưng luật có đúng dạng [batch_size, num_rules]
    if activations.ndim != 2 or activations.shape[0] != probs.shape[0]:
        raise ValueError("rule_features must have shape [batch_size, num_rules].")

    #Chuyển confidence thành tensor và đảm bảo cùng kiểu dữ liệu, thiết bị với xác suất dự đoán
    confidences = torch.as_tensor(
        rule_confidences, dtype=probs.dtype, device=probs.device
    )

    #Nếu confidence có dạng [R], mở rộng thành [B, R] để áp dụng cho toàn bộ batch
    if confidences.ndim == 1:
        confidences = confidences.unsqueeze(0).expand_as(activations)

    #Nếu confidence có dạng 2 chiều, kiểm tra kích thước phải trùng với rule_features
    elif confidences.shape != activations.shape:
        raise ValueError("rule_confidences must have shape [R] or [B, R].")

    #Tính trọng số của từng luật dựa trên mức độ kích hoạt và độ tin cậy
    #Chỉ những luật có confidence >= min_confidence mới được tham gia tính Logic Loss
    trusted_weights = (
        activations.clamp(0.0, 1.0)
        * confidences.clamp(0.0, 1.0)
        * (confidences >= min_confidence).to(probs.dtype)
    )

    #Tính tổng trọng số của các luật đáng tin cậy được kích hoạt trên từng mẫu
    per_sample_weight = trusted_weights.sum(dim=1)

    #Tính mức phạt theo cơ chế Hinge một chiều
    #Chỉ phạt khi có luật đáng tin cậy được kích hoạt nhưng xác suất phishing thấp hơn margin
    #Không ép xác suất dự đoán phải đạt 1 và không phạt khi không có luật được kích hoạt
    per_sample_penalty = F.relu(margin - probs).pow(2)

    #Xác định các mẫu có ít nhất một luật đáng tin cậy được kích hoạt
    valid = per_sample_weight > 0

    #Nếu không có mẫu nào thỏa mãn, trả về giá trị 0 vẫn duy trì khả năng tính gradient
    if not torch.any(valid):
        return probs.sum() * 0.0

    #Nhân mức phạt của từng mẫu với tổng trọng số các luật được kích hoạt
    weighted = per_sample_penalty[valid] * per_sample_weight[valid]

    #Tính Logic Loss trung bình có trọng số theo confidence của các luật
    return weighted.sum() / per_sample_weight[valid].sum().clamp_min(1e-8)


#Kết hợp Cross Entropy Loss và Symbolic Consistency Loss thành hàm mất mát tổng
def combined_loss(
    ce_loss: torch.Tensor,
    malicious_prob: torch.Tensor,
    rule_features: torch.Tensor,
    rule_confidences: torch.Tensor,
    logic_weight: float = 0.1,
    min_confidence: float = 0.75,
    margin: float = 0.90,
):

    #Tính Symbolic Consistency Loss dựa trên xác suất dự đoán và các luật được kích hoạt
    logic = symbolic_consistency_loss(
        malicious_prob=malicious_prob,
        rule_features=rule_features,
        rule_confidences=rule_confidences,
        min_confidence=min_confidence,
        margin=margin,
    )

    #Kết hợp Cross Entropy Loss và Logic Loss theo trọng số logic_weight
    #Trả về Loss tổng cùng các thành phần Loss riêng để theo dõi quá trình huấn luyện
    return ce_loss + logic_weight * logic, {
        "ce_loss": ce_loss.detach(),
        "logic_loss": logic.detach(),
    }
