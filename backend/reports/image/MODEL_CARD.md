# VerifyRX UK — Image Classifier (Model Card)

## Model summary

| Field | Value |
|---|---|
| **Name** | `verifyrx-uk/image-resnet18-finetuned` |
| **Task** | Binary classification — authentic vs counterfeit medicine pack |
| **Architecture** | `torchvision.models.resnet18` (ImageNet-1k pretrained), last residual block (`layer4`) + `fc` unfrozen, rest frozen |
| **Head** | `nn.Linear(512, 2)` replacing the 1000-class ImageNet head |
| **Class order** | `["authentic", "counterfeit"]` (alphabetical; enforced in `train_image.py`) |
| **Training data** | Student-curated on-disk dataset under `backend/data/images/` — 437 authentic + 240 counterfeit pack photos |
| **Training procedure** | Adam, lr 1e-4, batch 16, 5 epochs, best-val checkpointing, seed 42 |
| **Train/val split** | 80 / 20, `random.shuffle` seeded at 42 |
| **Augmentation (train)** | `RandomResizedCrop(224, scale=(0.7,1.0))`, `RandomHorizontalFlip`, `ColorJitter(0.2,0.2,0.2)` |
| **Preprocessing (eval)** | `Resize(256) → CenterCrop(224) → Normalize(ImageNet mean/std)` |
| **Live inference** | `services/image_classifier.py` |
| **Weights location** | `backend/models_cache/image/resnet18_finetuned.pt` (ignored by git) |
| **Loaded safely** | `torch.load(..., weights_only=True)` — pickle-RCE-safe |
| **Reproduction** | `cd backend && python -m scripts.train_image` |
| **Explainability** | Grad-CAM hooked on `layer4[-1]`, served as PNG at `/static/gradcams/<uuid>.png` |

## Intended use

The classifier is used **inside VerifyRX UK only** to inspect consumer
photographs of medicine packs (blister packs, outer cartons, labels) and
flag features inconsistent with a genuine product (misaligned holograms,
poor print registration, wrong batch-code format).

**Not intended for** regulated pharmaceutical QC, industrial line
inspection, diagnostic decisions, or any judgement about the safety of
the contents. A counterfeit pack may contain the correct drug; an
authentic-looking pack may contain the wrong one. Always advise a
consumer to verify through their pharmacist.

## Metrics

All numbers produced by `python -m scripts.evaluate_image` and live in
`backend/reports/image/metrics.json`.

### Validation split (in-distribution, n = 135)

Reconstructed deterministically from seed 42.

| Metric | Value |
|---|---|
| Accuracy | **0.993** |
| Precision | 0.980 |
| Recall | **1.000** |
| F1 | 0.990 |
| Expected Calibration Error (ECE, 10-bin over max-prob confidence) | **0.018** |

Confusion matrix (1 = counterfeit): **zero missed counterfeits**, 1 false
positive (authentic flagged as counterfeit).

### Ablation (identical val split)

Produced by `python -m scripts.ablation_image`.

| Model | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| random_head (ImageNet backbone + random 2-class fc, no training) | 0.370 | 0.35 | 0.84 | 0.497 |
| imagenet_logreg (frozen ImageNet features + sklearn LogisticRegression) | 0.978 | 0.96 | 0.98 | 0.970 |
| **finetuned_local** | **0.993** | **0.98** | **1.00** | **0.990** |

Two honest takeaways:

1. **ImageNet features are already strong.** A 512-d ImageNet avgpool
   feature + logistic regression hits 97.8 % — this task is not doing
   much work that ImageNet pretraining did not already do.

2. **Fine-tuning buys the last mile (and recall).** The + 1.5 %
   accuracy lift over logreg includes, crucially, a recall of 1.00 —
   no missed counterfeits on this val split. For a consumer safety
   tool this is the metric that matters.

## Known limitations

1. **Dataset is small and self-curated (~677 images).** The val split
   is only 135 images. A single-digit number of misclassifications
   moves the reported percentages substantially. Treat all point
   estimates with ±1.5 % uncertainty.

2. **No external test set.** In-house train and val draw from the
   same distribution; performance on unseen UK pack designs
   (retail-exclusive own-brand, foreign import) is unknown.

3. **Counterfeit source bias.** The "counterfeit" folder comes from
   a single "Fake/" pack of photos — the model may be learning
   photographic-setup artifacts (background, lighting) rather than
   product-level counterfeit cues. Grad-CAM heatmaps on the public
   UI should be inspected for whether attention sits on the *pack*
   or on surrounding context.

4. **No packaging-version drift handling.** A genuine pack redesign
   (holographic label update, new batch-code format) will look
   "counterfeit" to this model until it is retrained.

5. **No multi-view reasoning.** Single image per inference. A real
   counterfeit detection workflow benefits from comparing batch code,
   box, and blister pack together.

6. **Demo-mode fallback is effectively random.** If no fine-tuned
   weights are present the service runs with a randomly-initialised
   2-class head (accuracy ≈ 0.37). The API exposes
   `is_finetuned: false` so the UI can warn the user — verify that
   warning is rendered before any public demo.

## Ethical considerations

* **A false "counterfeit" verdict can cause a user to discard
  legitimate, life-sustaining medication.** The UI must make clear
  this is an indicator, not a verdict, and must recommend
  verification via pharmacist or MHRA before any action.

* **A false "authentic" verdict can mislead a user into consuming
  counterfeit product.** Because the stakes are asymmetric, recall on
  counterfeits should be preserved even at a precision cost.

* **Photos are processed locally; no image is forwarded to any
  external API.** Grad-CAM heatmaps are written to disk under
  `backend/static/gradcams/` and the directory is pruned to 100
  files. `backend/.gitignore` blocks the directory from being
  committed.

* **Training photos are the student's own and are never
  redistributed.** `data/images/` is listed in `.gitignore` for
  exactly this reason.

## Maintenance

* Retrain: `cd backend && python -m scripts.train_image`
* Regenerate metrics: `python -m scripts.evaluate_image`
* Regenerate ablation: `python -m scripts.ablation_image`
* All figures: `backend/reports/image/figures/`
* Update *this file's numbers* whenever `metrics.json` changes.
