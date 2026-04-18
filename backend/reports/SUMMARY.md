# VerifyRX UK — Evaluation Summary

_Generated: 2026-04-18T22:31:08+00:00_

Regenerate this file with:

```bash
cd backend
python -m scripts.generate_evaluation_report
```

## Pipeline status

| Step | Status | Elapsed |
|---|---|---|
| pytest (backend smoke) | ok | 22.9s |
| evaluate_sms | ok | 21.3s |
| ablation_sms (ood + uci) | ok | 25.3s |
| evaluate_image | ok | 5.5s |
| ablation_image | ok | 15.2s |

## SMS classifier — metrics

_Generated: 2026-04-18T22:30:07+00:00_

Model source: `/Users/hakku/thesis/backend/models_cache/sms`  (fine-tuned: True)

| Split | n | Accuracy | Precision | Recall | F1 | ECE |
|---|---|---|---|---|---|---|
| uci_heldout | 837 | 0.990 | 0.991 | 0.937 | 0.963 | 0.004 |
| ood_pharma | 30 | 0.733 | 0.667 | 0.933 | 0.778 | 0.224 |

**OOD per-category accuracy**

| Category | n | Accuracy | F1 |
|---|---|---|---|
| conversational | 3 | 1.000 | 0.000 |
| free-trial-offer | 3 | 1.000 | 1.000 |
| gp-legitimate | 3 | 0.000 | 0.000 |
| illicit-marketplace | 3 | 0.667 | 0.800 |
| logistics-legitimate | 3 | 0.000 | 0.000 |
| nhs-impersonation | 3 | 1.000 | 1.000 |
| personal-mentions-meds | 3 | 1.000 | 0.000 |
| pharmacy-impersonation | 3 | 1.000 | 1.000 |
| pharmacy-operational | 3 | 0.667 | 0.000 |
| regulator-impersonation | 3 | 1.000 | 1.000 |

Figures:
- `sms/figures/confusion_uci.png`
- `sms/figures/confusion_ood.png`
- `sms/figures/reliability_uci.png`
- `sms/figures/reliability_ood.png`

## SMS classifier — ablation

_Generated: 2026-04-18T22:30:46+00:00_

| Model | Split | n | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| majority | ood | 30 | 0.500 | 0.000 | 0.000 | 0.000 |
| keyword_rule | ood | 30 | 0.867 | 1.000 | 0.733 | 0.846 |
| pretrained_hub | ood | 30 | 0.667 | 0.857 | 0.400 | 0.545 |
| finetuned_local | ood | 30 | 0.733 | 0.667 | 0.933 | 0.778 |
| majority | uci | 837 | 0.867 | 0.000 | 0.000 | 0.000 |
| keyword_rule | uci | 837 | 0.873 | 0.857 | 0.054 | 0.102 |
| pretrained_hub | uci | 837 | 0.983 | 0.980 | 0.892 | 0.934 |
| finetuned_local | uci | 837 | 0.990 | 0.991 | 0.937 | 0.963 |

Figures: `sms/figures/ablation_ood.png`, `sms/figures/ablation_uci.png`

## Image classifier — metrics

_Generated: 2026-04-18T22:30:52+00:00_

Weights: `/Users/hakku/thesis/backend/models_cache/image/resnet18_finetuned.pt`  (fine-tuned: True)
Split: seed=42, val_frac=0.2, class_order=['authentic', 'counterfeit']

| Split | n | Accuracy | Precision | Recall | F1 | ECE |
|---|---|---|---|---|---|---|
| val | 135 | 0.993 | 0.980 | 1.000 | 0.990 | 0.018 |

Confusion matrix: tp=50, tn=84, fp=1, fn=0

Figures: `image/figures/confusion_val.png`, `image/figures/reliability_val.png`

## Image classifier — ablation

_Generated: 2026-04-18T22:31:08+00:00_

Split: seed=42, val_frac=0.2, n_train=542, n_val=135

| Model | n | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| random_head | 135 | 0.370 | 0.353 | 0.840 | 0.497 |
| imagenet_logreg | 135 | 0.978 | 0.961 | 0.980 | 0.970 |
| finetuned_local | 135 | 0.993 | 0.980 | 1.000 | 0.990 |

Figures: `image/figures/ablation_val.png`

## Model cards

- [`sms/MODEL_CARD.md`](sms/MODEL_CARD.md) — provenance, intended use, limitations.
- [`image/MODEL_CARD.md`](image/MODEL_CARD.md) — provenance, intended use, limitations.

