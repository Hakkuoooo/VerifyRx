"""
Out-of-distribution evaluation set for the fine-tuned SMS classifier.

Motivation:
    The UCI SMS Spam Collection (used for fine-tuning) is dominated by
    generic scams from ~2012: prize wins, ringtone subscriptions, dating
    chat lines. VerifyRX UK's thesis claim is that the model generalises
    to *pharma-themed* phishing — NHS refunds, fake prescription pickup
    alerts, counterfeit-drug marketplaces, MHRA / FDA impersonation.
    None of those appear in UCI.

Contents:
    30 hand-curated examples, balanced 15 scam / 15 legitimate,
    grouped into sub-scenarios so the thesis evaluation chapter can
    break out per-category performance. The groups are an honest
    reflection of threats a UK medicine consumer might see.

Usage:
    This module is imported by both `evaluate_sms.py` (metrics harness)
    and `ablation_sms.py` (baseline comparison). It can also be run
    directly for a quick sanity check:
        cd backend
        python -m scripts.evaluate_sms_ood
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sample:
    text: str
    label: str        # "scam" or "legitimate"
    category: str     # sub-scenario tag for per-category metrics


# ----------------------------------------------------------------------
# Scam examples. Five sub-categories, three examples each (= 15 total).
# ----------------------------------------------------------------------
SCAM_SAMPLES: list[Sample] = [
    # --- NHS impersonation ---
    Sample(
        "URGENT: Your NHS refund of £285.47 is pending. Claim now at "
        "bit.ly/nhs-refund-uk to avoid cancellation.",
        "scam",
        "nhs-impersonation",
    ),
    Sample(
        "NHS Alert: We attempted to deliver your prescription. Pay the "
        "£1.99 redelivery fee here: nhs-redeliver.co/pay",
        "scam",
        "nhs-impersonation",
    ),
    Sample(
        "NHS: You owe £47.20 for unpaid prescriptions. Settle now to "
        "avoid a county court judgement. nhs-penalty.uk",
        "scam",
        "nhs-impersonation",
    ),
    # --- Pharmacy / retailer impersonation ---
    Sample(
        "Your Boots Pharmacy order #8842 could not be processed. "
        "Update payment: boots-pharmacy-billing.com",
        "scam",
        "pharmacy-impersonation",
    ),
    Sample(
        "LloydsDirect: your repeat prescription has been held. Verify "
        "your account within 24h: lloyds-verify.info",
        "scam",
        "pharmacy-impersonation",
    ),
    Sample(
        "Superdrug Pharmacy: Click here to claim your £50 loyalty "
        "refund before it expires today. superdrug-loyalty.co",
        "scam",
        "pharmacy-impersonation",
    ),
    # --- Regulator impersonation ---
    Sample(
        "MHRA notice: your recent order of semaglutide has been flagged. "
        "Verify identity: mhra-verify.uk/login",
        "scam",
        "regulator-impersonation",
    ),
    Sample(
        "FDA WARNING: unauthorised drug detected in your recent order. "
        "Contact compliance immediately: fda-recall.us/form",
        "scam",
        "regulator-impersonation",
    ),
    Sample(
        "GPhC notification: your pharmacy registration requires urgent "
        "renewal. Click gphc-renewal.org within 48 hours.",
        "scam",
        "regulator-impersonation",
    ),
    # --- Illicit marketplace / no-prescription pharmacy ---
    Sample(
        "Cheap Viagra, Cialis, Xanax no prescription needed. 80% off "
        "this week only. meds4less.shop",
        "scam",
        "illicit-marketplace",
    ),
    Sample(
        "Hi, I'm Dr. Smith from Apollo Clinic. We can ship genuine "
        "painkillers without a script. WhatsApp +447700900123",
        "scam",
        "illicit-marketplace",
    ),
    Sample(
        "Generic Ozempic direct from the lab, no Rx, next-day UK. "
        "Telegram @pharma_direct_uk for menu",
        "scam",
        "illicit-marketplace",
    ),
    # --- Free-trial / too-good-to-be-true offers ---
    Sample(
        "CONGRATULATIONS! You've been selected for a free Ozempic trial. "
        "Claim here: ozempic-trial-uk.info",
        "scam",
        "free-trial-offer",
    ),
    Sample(
        "Dear customer, your private prescription is ready for pickup. "
        "Confirm within 24h or it will be destroyed: click rx-uk.net",
        "scam",
        "free-trial-offer",
    ),
    Sample(
        "Free weight-loss injection kit! Limited to the first 100 "
        "sign-ups in London. slim-kit.co.uk/claim",
        "scam",
        "free-trial-offer",
    ),
]


# ----------------------------------------------------------------------
# Legitimate examples. Five sub-categories, three examples each.
# ----------------------------------------------------------------------
LEGIT_SAMPLES: list[Sample] = [
    # --- Genuine pharmacy operational ---
    Sample(
        "Your Boots online order is out for delivery today between "
        "09:00 and 13:00. Tracking: boots.com/orders",
        "legitimate",
        "pharmacy-operational",
    ),
    Sample(
        "Hi James, your repeat prescription request has been approved "
        "and is ready to collect from the pharmacy after 4pm tomorrow.",
        "legitimate",
        "pharmacy-operational",
    ),
    Sample(
        "Thanks for your order from LloydsDirect. It will be dispatched "
        "within 2 working days.",
        "legitimate",
        "pharmacy-operational",
    ),
    # --- GP surgery / NHS legitimate ---
    Sample(
        "Reminder from Greenlight Surgery: your blood test is booked "
        "for Tuesday 10:15. Reply CANCEL to cancel.",
        "legitimate",
        "gp-legitimate",
    ),
    Sample(
        "NHS: Your COVID-19 booster invitation. Book at "
        "www.nhs.uk/book-covid or call 119. Do not reply.",
        "legitimate",
        "gp-legitimate",
    ),
    Sample(
        "Appointment confirmed: Dr. Patel, 2026-04-22 at 11:30. Please "
        "arrive 10 minutes early.",
        "legitimate",
        "gp-legitimate",
    ),
    # --- Personal messages mentioning medicine ---
    Sample(
        "Hi mum, running late from the pharmacy, be home by 6. Want me "
        "to grab dinner?",
        "legitimate",
        "personal-mentions-meds",
    ),
    Sample(
        "Hi love, can you pick up my prescription from Superdrug on the "
        "way home? Cheers x",
        "legitimate",
        "personal-mentions-meds",
    ),
    Sample(
        "Dad just picked up my inhaler. All fine. Will ring later x",
        "legitimate",
        "personal-mentions-meds",
    ),
    # --- Delivery / logistics (genuine) ---
    Sample(
        "Your parcel has been delivered to your safe place. Photo "
        "available in the Royal Mail app.",
        "legitimate",
        "logistics-legitimate",
    ),
    Sample(
        "DPD: your parcel will arrive between 12:04 and 13:04 today. "
        "Track live at dpd.co.uk",
        "legitimate",
        "logistics-legitimate",
    ),
    Sample(
        "Amazon: your order of Boots-branded vitamin D3 has been "
        "dispatched and will arrive Thursday.",
        "legitimate",
        "logistics-legitimate",
    ),
    # --- Generic conversational ---
    Sample(
        "Happy birthday! Lunch at Dishoom Saturday 1pm still on?",
        "legitimate",
        "conversational",
    ),
    Sample(
        "Running 10 min late, sorry!",
        "legitimate",
        "conversational",
    ),
    Sample(
        "Don't forget the milk on the way back please",
        "legitimate",
        "conversational",
    ),
]


EVAL_SET: list[Sample] = SCAM_SAMPLES + LEGIT_SAMPLES
assert len(EVAL_SET) == 30, f"expected 30 samples, got {len(EVAL_SET)}"


def _bar(label: str) -> None:
    print("\n" + label)
    print("-" * len(label))


def main() -> None:
    """Standalone sanity check — for a full metrics run use evaluate_sms.py."""
    from services import sms_classifier

    print(f"VerifyRX UK — SMS out-of-distribution evaluation")
    print(f"n = {len(EVAL_SET)} hand-curated pharma-themed samples")

    sms_classifier.classify("warmup")

    tp = tn = fp = fn = 0
    wrong: list[tuple[Sample, dict]] = []

    _bar("Per-example predictions")
    print(f"{'gt':10s}  {'pred':10s}  {'conf':6s}  text")
    for s in EVAL_SET:
        out = sms_classifier.classify(s.text)
        pred = out["prediction"]
        conf = out["confidence"]
        mark = "[OK]" if pred == s.label else "[MISS]"
        short = s.text[:70] + ("…" if len(s.text) > 70 else "")
        print(f"{s.label:10s}  {pred:10s}  {conf:.3f}  {mark} {short}")

        if pred == s.label:
            if s.label == "scam":
                tp += 1
            else:
                tn += 1
        else:
            wrong.append((s, out))
            if s.label == "scam":
                fn += 1
            else:
                fp += 1

    _bar("Confusion matrix (rows = ground truth)")
    print(f"               pred=scam   pred=legit")
    print(f"gt=scam        {tp:>9d}   {fn:>10d}")
    print(f"gt=legitimate  {fp:>9d}   {tn:>10d}")

    total = tp + tn + fp + fn
    acc = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    _bar("Metrics")
    print(f"accuracy   = {acc:.3f}  ({tp + tn}/{total})")
    print(f"precision  = {precision:.3f}")
    print(f"recall     = {recall:.3f}")
    print(f"f1         = {f1:.3f}")

    is_finetuned = sms_classifier._load()["is_finetuned"]
    source = sms_classifier._load()["source"]
    _bar("Model provenance")
    print(f"fine-tuned = {is_finetuned}")
    print(f"source     = {source}")

    if wrong:
        _bar("Misclassified examples (for thesis error analysis)")
        for s, out in wrong:
            print(f"  gt={s.label}  pred={out['prediction']}  conf={out['confidence']:.3f}  [{s.category}]")
            print(f"    {s.text}")


if __name__ == "__main__":
    main()
