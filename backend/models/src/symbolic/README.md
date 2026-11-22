# Symbolic module for URL BERT

Copy this folder to `src/symbolic/`. The existing misspelled filename
`knowlegde_base.py` is retained to match the project tree.

## Quick test

```python
from src.symbolic import SymbolicReasoner

reasoner = SymbolicReasoner()
result = reasoner.reason("http://paypal-login.example.xyz/verify-account")

print(result.score)
print(result.predicted_label)  # 0 or 1: rule-based signal only
print(result.active_rules)
print(result.feature_vector)   # fixed order defined by RULE_NAMES
```

## Generate features for a dataframe

```python
from src.symbolic import URLRuleExtractor, RULE_NAMES

extractor = URLRuleExtractor()
X_symbolic = extractor.transform(df["clean_url"].fillna("").tolist())

# Optional:
# df[RULE_NAMES] = pd.DataFrame(X_symbolic, index=df.index, columns=RULE_NAMES)
```

## Use the logic loss in PyTorch

`rule_features` must be the same 12-dimensional vector produced by the
extractor, in `RULE_NAMES` order. Class index 1 is assumed to mean malicious.

```python
import torch
from src.symbolic import KnowledgeBase
from src.symbolic.logic_loss import combined_loss

kb = KnowledgeBase()
rule_confidences = torch.tensor(
    kb.confidence_vector(RULE_NAMES), dtype=torch.float32, device=device
)

# In your training loop:
logits = model(input_ids, attention_mask, symbolic_features)
ce = criterion(logits, labels)
prob_malicious = torch.softmax(logits, dim=1)[:, 1]

loss, loss_parts = combined_loss(
    ce_loss=ce,
    malicious_prob=prob_malicious,
    rule_features=symbolic_features,
    rule_confidences=rule_confidences,
    logic_weight=0.1,
)
```

Start with `logic_weight=0.05` or `0.1`, then tune on validation data.
Do not tune thresholds or rule weights on the test set.

## Important caveats

- These rules are heuristic. A URL containing `login`, using an IP, or
  having a long path is not automatically malicious.
- The brand list is intentionally small and must be maintained carefully.
- The fallback registered-domain parser is approximate. For robust brand
  matching, install `tldextract` and use a pinned Public Suffix List snapshot.
- Check label mapping. This implementation assumes `0=benign`, `1=malicious`.
- Calculate symbolic features independently for train/validation/test.
  Never use labels to create rule activations.
- Inspect precision/recall of each rule on validation data before enabling
  it in the logic loss. In particular, the current high-confidence subset
  is deliberately small.
