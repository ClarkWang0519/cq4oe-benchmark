#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_all_cq2term.py

Walks 01_predictions/<model>/, runs eval_cq_terms.py for each (model, dataset)
pair, and refreshes the leaderboard at the end of a successful run.

Standard call:
    cd CQ2Term
    python -u scripts/run_all_cq2term.py

Run on a subset of models:
    python -u scripts/run_all_cq2term.py --models my_model

Run on a subset of datasets:
    python -u scripts/run_all_cq2term.py --datasets wine,awo

Skip the leaderboard refresh:
    python -u scripts/run_all_cq2term.py --no_leaderboard
"""
import argparse
import subprocess
import sys
from pathlib import Path

import os
PYTHON = os.environ.get("CQ4OE_PYTHON", sys.executable)

PRED_ROOT = Path("01_predictions")
GOLD_ROOT = Path("00_gold_standard")
EVAL_ROOT = Path("03_evaluation_results")
SUMMARY_ROOT = Path("04_summary")

DATASETS = ["wine", "vgo", "swo", "awo", "odrl", "water"]

# leaderboard/ sits at the repo root, one level above CQ2Term/.
LEADERBOARD_DIR = Path("../leaderboard")


def run(cmd):
    print("\n" + "=" * 100)
    print(" ".join(str(x) for x in cmd))
    print("=" * 100)
    subprocess.run([str(x) for x in cmd], check=True)


def find_gold_cq_terms(dataset):
    folder = GOLD_ROOT / dataset
    candidates = [
        folder / "cq_terms" / f"cq_to_terms_{dataset}.json",
        folder / f"cq_to_terms_{dataset}.json",
        folder / "cq_terms" / "cq_to_terms.json",
        folder / "cq_to_terms.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def find_pred_cq_terms(model_dir, dataset):
    candidates = [
        model_dir / "cq_terms" / f"{dataset}_terms.json",
        model_dir / f"{dataset}_terms.json",
        model_dir / "terms" / f"{dataset}_terms.json",
        model_dir / "terms" / f"{dataset}_cq2terms_terms.json",
        model_dir / "terms" / f"{dataset}_cq2term_cq2terms_terms.json",
        model_dir / "cq_terms" / f"{dataset}_cq2terms_terms.json",
        model_dir / "cq_terms" / f"{dataset}_cq2term_cq2terms_terms.json",
    ]
    for p in candidates:
        if p.exists():
            return p

    matches = sorted(model_dir.rglob(f"{dataset}*terms.json"))
    if matches:
        if len(matches) > 1:
            print(f"  [warn] {model_dir.name}/{dataset}: matched "
                  f"{len(matches)} files via fallback glob, picking "
                  f"{matches[0].name}")
        return matches[0]
    return None


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--models", default=None,
                   help="Comma-separated subset of model folder names. "
                        "Default: all model folders under 01_predictions/")
    p.add_argument("--datasets", default=None,
                   help="Comma-separated subset of datasets. "
                        f"Default: {','.join(DATASETS)}")
    p.add_argument("--no_leaderboard", action="store_true",
                   help="Skip the leaderboard refresh at the end")
    args = p.parse_args()

    if args.models:
        args.models_list = [m.strip() for m in args.models.split(",") if m.strip()]
    else:
        args.models_list = None  # filled in main() from filesystem

    if args.datasets:
        args.datasets_list = [d.strip() for d in args.datasets.split(",") if d.strip()]
        unknown = set(args.datasets_list) - set(DATASETS)
        if unknown:
            sys.exit(f"Unknown dataset(s): {sorted(unknown)}. "
                     f"Pick from: {DATASETS}")
    else:
        args.datasets_list = DATASETS

    return args


def refresh_leaderboard():
    """Call build_leaderboard.py from the leaderboard directory."""
    script = LEADERBOARD_DIR / "build_leaderboard.py"
    if not script.exists():
        print(f"WARN: {script} not found, leaderboard not refreshed.")
        return
    cmd = [
        PYTHON, str(script),
        "--cq2term_root", "03_evaluation_results",
        "--cq2onto_root", "../CQ2Onto/03_evaluation_results",
        "--html_data",    str(LEADERBOARD_DIR / "leaderboard_data.js"),
        "--markdown_out", str(LEADERBOARD_DIR / "leaderboard.md"),
    ]
    print("\n" + "=" * 100)
    print("Refreshing leaderboard")
    print(" ".join(str(x) for x in cmd))
    print("=" * 100)
    try:
        subprocess.run([str(x) for x in cmd], check=True)
    except subprocess.CalledProcessError as e:
        print(f"WARN: leaderboard refresh failed with exit {e.returncode}, "
              f"but evaluation results were saved.")


def main():
    args = parse_args()

    all_model_dirs = sorted([
        p for p in PRED_ROOT.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ])

    if args.models_list:
        unknown = set(args.models_list) - {d.name for d in all_model_dirs}
        if unknown:
            sys.exit(f"Unknown model(s) under {PRED_ROOT}: {sorted(unknown)}")
        model_dirs = [d for d in all_model_dirs if d.name in args.models_list]
    else:
        model_dirs = all_model_dirs

    for model_dir in model_dirs:
        model = model_dir.name

        for dataset in args.datasets_list:
            gold_cq_terms = find_gold_cq_terms(dataset)
            pred_cq_terms = find_pred_cq_terms(model_dir, dataset)

            if gold_cq_terms is None:
                print(f"SKIP {model}/{dataset}: missing gold cq_to_terms")
                continue

            if pred_cq_terms is None:
                print(f"SKIP {model}/{dataset}: missing pred terms")
                continue

            print(f"\n### Running CQ2TERM / {model} / {dataset}")
            print(f"Gold CQ terms : {gold_cq_terms}")
            print(f"Pred CQ terms : {pred_cq_terms}")

            out_dir = EVAL_ROOT / model / dataset / "06_cq_terms"
            report_path = SUMMARY_ROOT / model / f"{dataset}_report.md"

            out_dir.mkdir(parents=True, exist_ok=True)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            run([
                PYTHON, "scripts/eval_cq_terms.py",
                "--gold_cq_to_terms", gold_cq_terms,
                "--pred_cq_to_terms", pred_cq_terms,
                "--methods", "hard_match,jaro_winkler,levenshtein,semantic,sequence_match",
                "--hard_threshold", "1.0",
                "--lexical_threshold", "0.75",
                "--semantic_threshold", "0.65",
                "--top_n", "3",
                "--final_threshold", "0.6",
                "--save_class_alignment_csv", out_dir / "cqterm_class_trace.csv",
                "--save_property_alignment_csv", out_dir / "cqterm_prop_trace.csv",
                "--save_class_best_matching_csv", out_dir / "cqterm_class_best_matching.csv",
                "--save_property_best_matching_csv", out_dir / "cqterm_prop_best_matching.csv",
                "--save_cq_coverage_csv", out_dir / "cq_coverage.csv",
                "--save_term_coverage_csv", out_dir / "term_coverage.csv",
                "--save_result_json", out_dir / "eval_cq_terms_result.json",
                "--save_report_md", report_path,
            ])

            print(f"DONE: CQ2TERM / {model} / {dataset}")

    if not args.no_leaderboard:
        refresh_leaderboard()


if __name__ == "__main__":
    main()
