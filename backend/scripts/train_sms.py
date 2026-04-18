"""
Fine-tune DistilBERT on the UCI SMS Spam Collection dataset.

Usage:
    cd backend
    python -m scripts.train_sms                      # default settings
    python -m scripts.train_sms --epochs 3 --batch 32

Dataset: the HuggingFace `sms_spam` dataset (5,574 messages, 13.4% spam)
is downloaded automatically on first run (~500 KB).

Output: tokenizer + model weights written to backend/models_cache/sms/.
Once that directory exists, services/sms_classifier.py picks it up
automatically on the next server restart.

Runtime: ~15–25 minutes on CPU for 2 epochs on a modern laptop. If you
have a CUDA GPU or Apple Silicon MPS, HuggingFace's Trainer will pick
it up without any flags.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from datasets import load_dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BACKEND_DIR / "models_cache" / "sms"
BASE_MODEL = "distilbert-base-uncased"

# Canonical label ordering. MUST match what sms_classifier.py expects
# (spam_idx=1). The source dataset uses 0=ham, 1=spam already.
LABEL_NAMES = ["ham", "spam"]


def _compute_metrics(eval_pred):
    """Accuracy + macro-F1 so you can see class-imbalance effects."""
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    accuracy = float((preds == labels).mean())
    # Per-class precision/recall, manual to avoid adding sklearn as a
    # training-time dep (runtime already has it for LIME).
    tp = ((preds == 1) & (labels == 1)).sum()
    fp = ((preds == 1) & (labels == 0)).sum()
    fn = ((preds == 0) & (labels == 1)).sum()
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr", type=float, default=5e-5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"[train_sms] Loading dataset 'sms_spam' …")
    raw = load_dataset("sms_spam", split="train")

    # UCI SMS Spam has no official train/test split; we create one.
    split = raw.train_test_split(test_size=0.15, seed=args.seed)
    train_ds, eval_ds = split["train"], split["test"]
    print(f"[train_sms] train={len(train_ds)}, eval={len(eval_ds)}")

    print(f"[train_sms] Loading tokenizer + model '{BASE_MODEL}' …")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=len(LABEL_NAMES),
        id2label={i: n for i, n in enumerate(LABEL_NAMES)},
        label2id={n: i for i, n in enumerate(LABEL_NAMES)},
    )

    def tokenize(batch):
        return tokenizer(
            batch["sms"], truncation=True, max_length=256
        )

    train_ds = train_ds.map(tokenize, batched=True).rename_column("label", "labels")
    eval_ds = eval_ds.map(tokenize, batched=True).rename_column("label", "labels")
    train_ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])
    eval_ds.set_format("torch", columns=["input_ids", "attention_mask", "labels"])

    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    training_args = TrainingArguments(
        output_dir=str(OUTPUT_DIR / "_trainer"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        per_device_eval_batch_size=args.batch,
        learning_rate=args.lr,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="no",
        logging_steps=50,
        seed=args.seed,
        report_to=[],  # disable wandb/tensorboard auto-detection
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=_compute_metrics,
    )

    print("[train_sms] Training …")
    trainer.train()

    print("[train_sms] Evaluating …")
    metrics = trainer.evaluate()
    print(f"[train_sms] Final metrics: {metrics}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(OUTPUT_DIR))
    tokenizer.save_pretrained(str(OUTPUT_DIR))
    print(f"[train_sms] Saved fine-tuned model to {OUTPUT_DIR}")
    print(
        "[train_sms] Restart uvicorn and the SMS endpoint will pick up "
        "the new weights automatically."
    )


if __name__ == "__main__":
    main()
