# VerifyRX UK — SMS Scam Classifier (Model Card)

## Model summary

| Field | Value |
|---|---|
| **Name** | `verifyrx-uk/sms-distilbert-finetuned` |
| **Task** | Binary classification — scam (spam/phishing) vs legitimate |
| **Architecture** | `distilbert-base-uncased`, 66 M parameters, 2-class classification head |
| **Training data** | UCI SMS Spam Collection (5,574 messages; 13.4 % spam, 86.6 % ham) |
| **Training procedure** | Hugging Face `Trainer`, 2 epochs, batch 16, lr 5e-5, weight decay 0.01, seed 42 |
| **Held-out split** | 15 %, seed 42, stratified via `train_test_split` |
| **Live inference** | `services/sms_classifier.py` (lazy-loaded singleton) |
| **Weights location** | `backend/models_cache/sms/` (ignored by git) |
| **Reproduction** | `cd backend && python -m scripts.train_sms` |

## Intended use

The classifier is used **inside VerifyRX UK only** to flag suspicious SMS
messages a UK consumer might receive about medicine (fake NHS refunds,
fake prescription-pickup alerts, unregulated Ozempic/semaglutide
marketplaces, MHRA/FDA impersonation).

**Not intended for** general spam filtering, foreign-language SMS,
non-medicine scams, regulated content moderation, or any decision that
would deny a user access to healthcare.

## Metrics

All numbers below are produced by
`python -m scripts.evaluate_sms` and live in
`backend/reports/sms/metrics.json`. Regenerate after any retraining.

### UCI SMS Spam Collection — held-out split (in-distribution, n = 837)

| Metric | Value |
|---|---|
| Accuracy | **0.990** |
| Precision | 0.991 |
| Recall | 0.937 |
| F1 | 0.963 |
| Expected Calibration Error (ECE, 10-bin, Guo et al. 2017) | **0.009** |

Confusion matrix: `tp = 104, tn = 725, fp = 1, fn = 7`.

### Out-of-distribution pharma SMS — hand-curated (n = 30)

30 hand-written samples across 10 sub-scenarios, balanced 15 scam / 15
legitimate. Source: `backend/scripts/evaluate_sms_ood.py`.

| Metric | Value |
|---|---|
| Accuracy | 0.733 |
| Precision | 0.667 |
| Recall | **0.933** |
| F1 | 0.778 |
| ECE | 0.244 |

Confusion matrix: `tp = 14, tn = 8, fp = 7, fn = 1`.

**Per-category OOD breakdown** (sample of note):

| Sub-category | Accuracy | Notes |
|---|---|---|
| nhs-impersonation | 1.00 | scam — all 3 caught |
| pharmacy-impersonation | 1.00 | scam — all 3 caught |
| regulator-impersonation | 1.00 | scam — MHRA/FDA/GPhC all caught |
| free-trial-offer | 1.00 | scam — all 3 caught |
| illicit-marketplace | 0.67 | scam — 1 missed ("Telegram @pharma_direct_uk") |
| pharmacy-operational | 0.67 | legit — 1 false positive on "Boots out-for-delivery" |
| gp-legitimate | **0.00** | legit — NHS COVID booster / blood-test reminders flagged as scam |
| logistics-legitimate | **0.00** | legit — DPD / Royal Mail / Amazon dispatch flagged as scam |
| personal-mentions-meds | 1.00 | legit — all 3 passed |
| conversational | 1.00 | legit — all 3 passed |

### Ablation (identical inputs)

Produced by `python -m scripts.ablation_sms`. Same splits, same
preprocessing, fair comparison.

| Model | Split | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|
| majority | UCI held-out | 0.867 | 0.00 | 0.00 | 0.000 |
| keyword_rule (25 regexes) | UCI held-out | 0.873 | 0.86 | 0.05 | 0.102 |
| pretrained_hub (bert-tiny) | UCI held-out | 0.983 | 0.98 | 0.89 | 0.934 |
| **finetuned_local** | **UCI held-out** | **0.990** | **0.99** | **0.94** | **0.963** |
| majority | OOD pharma | 0.500 | 0.00 | 0.00 | 0.000 |
| keyword_rule | OOD pharma | **0.867** | **1.00** | 0.73 | **0.846** |
| pretrained_hub | OOD pharma | 0.667 | 0.86 | 0.40 | 0.545 |
| finetuned_local | OOD pharma | 0.733 | 0.67 | **0.93** | 0.778 |

The keyword rule beats both transformers on OOD F1. This is honest
rather than embarrassing: the keyword list was hand-picked for the
exact 30-sample OOD distribution. Fine-tuning does beat both baselines
on **recall**, which is the metric that actually matters for a
counterfeit-medicine safety tool — a missed scam is a possible fake
prescription; a false positive on a legit pharmacy SMS is an
inconvenience.

## Known limitations

1. **Over-flags NHS/logistics legitimate SMS.** The model learned
   "NHS + short URL" and "parcel + tracking URL" as scam-adjacent
   because UCI SMS is dominated by generic prize-draw scams. A real
   deployment needs either (a) fine-tuning on authenticated-sender-
   aware data, or (b) an allowlist layer for verified NHS / Royal Mail
   / DPD sender IDs.

2. **Out-of-domain miscalibration.** ECE rises from 0.009 on UCI to
   0.244 on OOD. The model is over-confident on pharma-themed inputs.
   Temperature scaling (Guo et al. 2017) is an obvious improvement
   before deployment.

3. **Single language.** English only. A UK consumer receiving a
   Spanish / Urdu / Arabic pharma scam will not be protected.

4. **No adversarial robustness.** Character-level perturbations
   ("CLA1M NOW") are not in the training distribution and will likely
   lower recall. The LIME explainer is correspondingly unstable on
   obfuscated text.

5. **UCI is 2012-era data.** Modern scam vocabulary (crypto,
   semaglutide, weight-loss injections) is absent from training.
   This is precisely what the OOD eval is designed to surface.

6. **Risk score is `P(scam) × 100`.** It is *not* calibrated to any
   real-world notion of financial or medical risk; treat it as a
   ranking number, not a probability of harm.

## Ethical considerations

* **False positives can suppress legitimate NHS / pharmacy
  communication.** Any production deployment must include a clear
  appeal path — tell the user *why* the message was flagged (LIME
  weights are rendered in the UI) and let them override.

* **Training data (UCI SMS Spam Collection) has no consent from
  message senders.** It is publicly redistributed under the original
  Almeida et al. 2011 release; verify licensing for your
  jurisdiction before commercial use.

* **Do not use this model as the sole signal for blocking,
  reporting, or prosecuting a user.** It is one of three modules in
  VerifyRX UK; combine with the URL-checker and the image-classifier
  before any action.

## Maintenance

* Retrain: `cd backend && python -m scripts.train_sms`
* Regenerate metrics: `python -m scripts.evaluate_sms`
* Regenerate ablation: `python -m scripts.ablation_sms`
* All figures: `backend/reports/sms/figures/`
* Update *this file's numbers* whenever `metrics.json` changes.
