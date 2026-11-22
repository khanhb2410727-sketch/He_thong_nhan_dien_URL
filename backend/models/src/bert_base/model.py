import torch
import torch.nn as nn
from transformers import AutoModel

class BERTClassifier(nn.Module):
    def __init__(self, model_name="bert-base-uncased", num_classes=2, dropout=0.1):
        super().__init__()

        self.bert = AutoModel.from_pretrained(model_name)

        hidden_size = self.bert.config.hidden_size

        self.dropout = nn.Dropout(dropout)
        self.classifier = nn.Linear(hidden_size, num_classes)

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )

        embedding = outputs.last_hidden_state[:, 0, :]
        logits = self.classifier(
            self.dropout(embedding)
        )

        return {
            "logits": logits,
            "embedding": embedding
        }