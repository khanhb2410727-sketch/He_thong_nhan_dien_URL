import torch
import torch.nn as nn

from backend.models.src.bert_base.model import BERTClassifier
from backend.models.src.symbolic import SymbolicReasoner


class NeuralSymbolicModel(nn.Module):
    def __init__(
        self,
        model_name="bert-base-uncased",
        num_classes=2,
        symbolic_dim=12,
        fusion_hidden=128,
        dropout=0.1
    ):
        super().__init__()
        # Neural module
        self.neural = BERTClassifier(
            model_name=model_name,
            num_classes=num_classes,
            dropout=dropout
        )

        # Symbolic module
        self.reasoner = SymbolicReasoner()

        # Fusion module
        fusion_input_dim = num_classes + symbolic_dim + 1

        self.fusion = nn.Sequential(
            nn.Linear(fusion_input_dim, fusion_hidden),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fusion_hidden, num_classes)
        )

        self.symbolic_dim = symbolic_dim

    def forward(
        self,
        input_ids,
        attention_mask,
        urls,
        token_type_ids=None
    ):

        # 1. Neural prediction
        neural_output = self.neural(
            input_ids,
            attention_mask,
            token_type_ids
        )

        neural_logits = neural_output["logits"]
        neural_embedding = neural_output["embedding"]
        neural_probs = torch.softmax(
            neural_logits,
            dim=-1
        )

        # 2. Symbolic reasoning
        symbolic_results = [
            self.reasoner.reason(url)
            for url in urls
        ]

        symbolic_features = torch.tensor(
            [
                result.feature_vector
                for result in symbolic_results
            ],
            dtype=neural_probs.dtype,
            device=neural_probs.device
        )

        symbolic_scores = torch.tensor(
            [
                result.score
                for result in symbolic_results
            ],
            dtype=neural_probs.dtype,
            device=neural_probs.device
        ).unsqueeze(1)

        # 3. Feature fusion
        fusion_input = torch.cat(
            [
                neural_probs,
                symbolic_features,
                symbolic_scores
            ],
            dim=1
        )

        # 4. Final prediction
        final_logits = self.fusion(fusion_input)

        return {
            "logits": final_logits,
            "neural_logits": neural_logits,
            "neural_probs": neural_probs,
            "neural_embedding": neural_embedding,
            "symbolic_scores": symbolic_scores,
            "symbolic_features": symbolic_features,
            "symbolic_results": symbolic_results
        }