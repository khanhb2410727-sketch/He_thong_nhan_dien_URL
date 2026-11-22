from transformers import BertModel
import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import BertModel

class BayesianLinear(nn.Module):
    def __init__(self, in_features, out_features):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features

        # 2 bộ trọng số: Mu và Rho
        self.weight_mu = nn.Parameter(torch.Tensor(out_features, in_features).normal_(0, 0.02))
        self.weight_rho = nn.Parameter(torch.Tensor(out_features, in_features).normal_(-3, 0.1))

        self.bias_mu = nn.Parameter(torch.Tensor(out_features).normal_(0, 0.02))
        self.bias_rho = nn.Parameter(torch.Tensor(out_features).normal_(-3, 0.1))

        self.prior_sigma = 0.1

    def forward(self, x):
        weight_sigma = torch.log1p(torch.exp(self.weight_rho))
        bias_sigma = torch.log1p(torch.exp(self.bias_rho))

        # Lấy mẫu ngẫu nhiên
        epsilon_w = torch.randn_like(self.weight_mu)
        epsilon_b = torch.randn_like(self.bias_mu)

        weight = self.weight_mu + weight_sigma * epsilon_w
        bias = self.bias_mu + bias_sigma * epsilon_b

        return F.linear(x, weight, bias)


class BayesianBERT(nn.Module):
    def __init__(self):
        super().__init__()
        # 1. Tải BERT gốc
        self.bert = BertModel.from_pretrained('bert-base-uncased')

        # 2. Quét và thay thế các lớp Linear bằng BayesianLinear
        for name, module in self.bert.named_children():
            if isinstance(module, nn.Linear):
                # Lấy kích thước đầu vào/ra của lớp cũ
                in_f, out_f = module.in_features, module.out_features
                # Thay thế bằng lớp Bayesian
                setattr(self.bert, name, BayesianLinear(in_f, out_f))
            else:
                # Quét sâu vào bên trong các khối Transformer
                for sub_name, sub_module in module.named_children():
                    if isinstance(sub_module, nn.Linear):
                        in_f, out_f = sub_module.in_features, sub_module.out_features
                        setattr(module, sub_name, BayesianLinear(in_f, out_f))

        # 3. Lớp phân loại cuối cùng cũng phải là Bayesian
        self.classifier = BayesianLinear(self.bert.config.hidden_size, 2)

    def forward(self, input_ids, attention_mask):
        # Trích xuất đặc trưng từ BERT (nhưng bỏ qua lớp pooler mặc định)
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        # Lấy vector [CLS] (token đầu tiên)
        cls_token = outputs.last_hidden_state[:, 0, :]
        # Đưa qua lớp phân loại Bayesian
        logits = self.classifier(cls_token)
        return logits