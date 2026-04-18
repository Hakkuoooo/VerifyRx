"""
One-command thesis-evaluation runner.

Runs the whole apparatus end-to-end and writes a single top-level
`reports/SUMMARY.md` aggregating every metric, figure, and model card
produced by the individual scripts. A thesis reader (or an examiner)
can open that one file and get the complete picture.

Sub-steps (each a module invocation of an existing script):
  1. pytest (backend smoke tests)            — optional, enabled by default
  2. scripts.evaluate_sms                    — UCI + OOD metrics + figures
  3. scripts.ablation_sms                    — 4-way SMS ablation
  4. scripts.evaluate_image                  — val metrics + figures
  5. scripts.ablation_image                  — 3-way image ablation
  6. Render reports/SUMMARY.md from the two metrics.json + two ablation.json

Each sub-step is skippable, so a student running on a small laptop can
generate just the pieces they need. Sub-step failures are surfaced but
don't abort the rest of the run — you still get whatever artifacts
succeeded.

Usage:
    cd backend
    python -m scripts.generate_evaluation_report
    python -m scripts.generate_evaluation_report --skip-tests --skip-image-ablation
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "reports"
SUMMARY_PATH = REPORTS_DIR / "SUMMARY.md"


@dataclass
class Step:
    name: str
    command: list[str]
    skip: bool = False
    status: str = "pending"     # pending | ok | failed | skipped
    elapsed_s: float = 0.0
    stdout_tail: str = ""
    stderr_tail: str = ""


def _run(step: Step) -> None:
    """Run one step and record its outcome."""
    if step.skip:
        step.status = "skipped"
        return

    print(f"\n[report] ▶ {step.name}  ({' '.join(step.command)})")
    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            step.command,
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        step.status = "failed"
        step.stderr_tail = str(exc)
        return
    step.elapsed_s = time.perf_counter() - t0

    # Tail stdout/stderr so the summary isn't huge.
    def _tail(text: str, n: int = 40) -> str:
        lines = (text or "").strip().splitlines()
        return "\n".join(lines[-n:])

    step.stdout_tail = _tail(result.stdout)
    step.stderr_tail = _tail(result.stderr)
    step.status = "ok" if result.returncode == 0 else "failed"

    emoji = "OK " if step.status == "ok" else "FAIL"
    print(f"[report] {emoji} {step.name} in {step.elapsed_s:.1f}s")


# ---------------------------------------------------------------------------
# Summary rendering
# ---------------------------------------------------------------------------
def _read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def _fmt_metric(v: float | int | None) -> str:
    if v is None:
        return "—"
    if isinstance(v, int):
        return str(v)
    return f"{v:.3f}"


def _sms_metrics_block(sms_metrics: dict | None) -> str:
    if sms_metrics is None:
        return "_SMS metrics not available — run `python -m scripts.evaluate_sms`._\n"

    lines: list[str] = []
    lines.append(f"_Generated: {sms_metrics.get('generated_at', '—')}_")
    lines.append("")
    lines.append(f"Model source: `{sms_metrics['model']['source']}`  "
                 f"(fine-tuned: {sms_metrics['model']['is_finetuned']})")
    lines.append("")
    lines.append("| Split | n | Accuracy | Precision | Recall | F1 | ECE |")
    lines.append("|---|---|---|---|---|---|---|")
    for split_name, split in sms_metrics.get("splits", {}).items():
        lines.append(
            f"| {split_name} | {split['n']} | "
            f"{_fmt_metric(split['accuracy'])} | "
            f"{_fmt_metric(split['precision'])} | "
            f"{_fmt_metric(split['recall'])} | "
            f"{_fmt_metric(split['f1'])} | "
            f"{_fmt_metric(split['ece'])} |"
        )

    # Per-category OOD breakdown (most interesting for the thesis)
    ood = sms_metrics.get("splits", {}).get("ood_pharma", {})
    per_cat = ood.get("per_category", {}) if ood else {}
    if per_cat:
        lines.append("")
        lines.append("**OOD per-category accuracy**")
        lines.append("")
        lines.append("| Category | n | Accuracy | F1 |")
        lines.append("|---|---|---|---|")
        for cat, m in sorted(per_cat.items()):
            lines.append(
                f"| {cat} | {m['n']} | "
                f"{_fmt_metric(m['accuracy'])} | "
                f"{_fmt_metric(m['f1'])} |"
            )
    return "\n".join(lines) + "\n"


def _sms_ablation_block(abl: dict | None) -> str:
    if abl is None:
        return "_SMS ablation not available — run `python -m scripts.ablation_sms`._\n"

    lines: list[str] = []
    lines.append(f"_Generated: {abl.get('generated_at', '—')}_")
    lines.append("")
    lines.append("| Model | Split | n | Accuracy | Precision | Recall | F1 |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in abl.get("rows", []):
        lines.append(
            f"| {r['model']} | {r['split']} | {r['n']} | "
            f"{_fmt_metric(r['accuracy'])} | "
            f"{_fmt_metric(r['precision'])} | "
            f"{_fmt_metric(r['recall'])} | "
            f"{_fmt_metric(r['f1'])} |"
        )
    return "\n".join(lines) + "\n"


def _image_metrics_block(img: dict | None) -> str:
    if img is None:
        return "_Image metrics not available — run `python -m scripts.evaluate_image`._\n"

    lines: list[str] = []
    lines.append(f"_Generated: {img.get('generated_at', '—')}_")
    lines.append("")
    lines.append(f"Weights: `{img['model'].get('weights_path', '—')}`  "
                 f"(fine-tuned: {img['model'].get('is_finetuned', '—')})")
    lines.append(f"Split: seed={img['split']['seed']}, "
                 f"val_frac={img['split']['val_frac']}, "
                 f"class_order={img['split']['class_order']}")
    lines.append("")
    m = img.get("metrics", {})
    lines.append("| Split | n | Accuracy | Precision | Recall | F1 | ECE |")
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(
        f"| val | {m.get('n', '—')} | "
        f"{_fmt_metric(m.get('accuracy'))} | "
        f"{_fmt_metric(m.get('precision'))} | "
        f"{_fmt_metric(m.get('recall'))} | "
        f"{_fmt_metric(m.get('f1'))} | "
        f"{_fmt_metric(m.get('ece'))} |"
    )
    cm = m.get("confusion_matrix", {})
    lines.append("")
    lines.append(f"Confusion matrix: tp={cm.get('tp')}, "
                 f"tn={cm.get('tn')}, fp={cm.get('fp')}, fn={cm.get('fn')}")
    return "\n".join(lines) + "\n"


def _image_ablation_block(abl: dict | None) -> str:
    if abl is None:
        return "_Image ablation not available — run `python -m scripts.ablation_image`._\n"

    lines: list[str] = []
    lines.append(f"_Generated: {abl.get('generated_at', '—')}_")
    lines.append("")
    sp = abl.get("split", {})
    lines.append(
        f"Split: seed={sp.get('seed')}, val_frac={sp.get('val_frac')}, "
        f"n_train={sp.get('n_train')}, n_val={sp.get('n_val')}"
    )
    lines.append("")
    lines.append("| Model | n | Accuracy | Precision | Recall | F1 |")
    lines.append("|---|---|---|---|---|---|")
    for r in abl.get("rows", []):
        lines.append(
            f"| {r['model']} | {r['n']} | "
            f"{_fmt_metric(r['accuracy'])} | "
            f"{_fmt_metric(r['precision'])} | "
            f"{_fmt_metric(r['recall'])} | "
            f"{_fmt_metric(r['f1'])} |"
        )
    return "\n".join(lines) + "\n"


def _steps_block(steps: list[Step]) -> str:
    lines: list[str] = []
    lines.append("| Step | Status | Elapsed |")
    lines.append("|---|---|---|")
    for s in steps:
        elapsed = f"{s.elapsed_s:.1f}s" if s.status == "ok" else "—"
        lines.append(f"| {s.name} | {s.status} | {elapsed} |")
    return "\n".join(lines) + "\n"


def _write_summary(steps: list[Step]) -> None:
    sms_metrics = _read_json(REPORTS_DIR / "sms" / "metrics.json")
    sms_ablation = _read_json(REPORTS_DIR / "sms" / "ablation.json")
    image_metrics = _read_json(REPORTS_DIR / "image" / "metrics.json")
    image_ablation = _read_json(REPORTS_DIR / "image" / "ablation.json")

    body: list[str] = []
    body.append("# VerifyRX UK — Evaluation Summary")
    body.append("")
    body.append(f"_Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_")
    body.append("")
    body.append("Regenerate this file with:")
    body.append("")
    body.append("```bash")
    body.append("cd backend")
    body.append("python -m scripts.generate_evaluation_report")
    body.append("```")
    body.append("")
    body.append("## Pipeline status")
    body.append("")
    body.append(_steps_block(steps))
    body.append("## SMS classifier — metrics")
    body.append("")
    body.append(_sms_metrics_block(sms_metrics))
    body.append("Figures:")
    body.append("- `sms/figures/confusion_uci.png`")
    body.append("- `sms/figures/confusion_ood.png`")
    body.append("- `sms/figures/reliability_uci.png`")
    body.append("- `sms/figures/reliability_ood.png`")
    body.append("")
    body.append("## SMS classifier — ablation")
    body.append("")
    body.append(_sms_ablation_block(sms_ablation))
    body.append("Figures: `sms/figures/ablation_ood.png`, `sms/figures/ablation_uci.png`")
    body.append("")
    body.append("## Image classifier — metrics")
    body.append("")
    body.append(_image_metrics_block(image_metrics))
    body.append("Figures: `image/figures/confusion_val.png`, `image/figures/reliability_val.png`")
    body.append("")
    body.append("## Image classifier — ablation")
    body.append("")
    body.append(_image_ablation_block(image_ablation))
    body.append("Figures: `image/figures/ablation_val.png`")
    body.append("")
    body.append("## Model cards")
    body.append("")
    body.append("- [`sms/MODEL_CARD.md`](sms/MODEL_CARD.md) — provenance, intended use, limitations.")
    body.append("- [`image/MODEL_CARD.md`](image/MODEL_CARD.md) — provenance, intended use, limitations.")
    body.append("")

    SUMMARY_PATH.write_text("\n".join(body) + "\n")
    print(f"\n[report] Summary written to {SUMMARY_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true",
                        help="Skip backend pytest smoke tests.")
    parser.add_argument("--skip-sms", action="store_true")
    parser.add_argument("--skip-sms-ablation", action="store_true")
    parser.add_argument("--skip-image", action="store_true")
    parser.add_argument("--skip-image-ablation", action="store_true")
    args = parser.parse_args()

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Reuse the same Python executable so venvs are respected.
    py = sys.executable

    steps = [
        Step(
            "pytest (backend smoke)",
            [py, "-m", "pytest", "-q"],
            skip=args.skip_tests,
        ),
        Step(
            "evaluate_sms",
            [py, "-m", "scripts.evaluate_sms"],
            skip=args.skip_sms,
        ),
        Step(
            "ablation_sms (ood + uci)",
            [py, "-m", "scripts.ablation_sms", "--splits", "ood", "uci"],
            skip=args.skip_sms_ablation,
        ),
        Step(
            "evaluate_image",
            [py, "-m", "scripts.evaluate_image"],
            skip=args.skip_image,
        ),
        Step(
            "ablation_image",
            [py, "-m", "scripts.ablation_image"],
            skip=args.skip_image_ablation,
        ),
    ]

    for s in steps:
        _run(s)

    _write_summary(steps)

    # Final one-line status so CI / Make can `| tee` this.
    failed = [s for s in steps if s.status == "failed"]
    if failed:
        print(f"\n[report] {len(failed)} step(s) failed: "
              + ", ".join(s.name for s in failed))
        # Non-zero exit so a `make report` fails loudly, but we still
        # wrote the SUMMARY above with whatever succeeded.
        sys.exit(1)
    print("\n[report] all steps OK")


if __name__ == "__main__":
    main()
