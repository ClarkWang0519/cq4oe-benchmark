#!/usr/bin/env python3
"""
collect_into_submission.py

Copies the evaluation outputs the runners produced into a NEW folder inside the
submission itself:

    submissions/<name>/evaluation/
        CQ2Term/<domain>/...            (per-domain result jsons + csvs)
        CQ2Term/_summary/<domain>_report.md
        CQ2Onto/<domain>/...
        CQ2Onto/_summary/<domain>_report.md
        SUMMARY.md                      (headline F1s + stamp)

Source layout produced by the runners:
    CQ2Term/03_evaluation_results/<name>/<domain>/06_cq_terms/eval_cq_terms_result.json
    CQ2Term/04_summary/<name>/<domain>_report.md
    CQ2Onto/03_evaluation_results/<mode>/<name>/<domain>/<layer>/*result.json
    CQ2Onto/04_summary/<mode>/<name>/<domain>/..._report.md
"""
import argparse, json, shutil, datetime
from pathlib import Path

def cq2term_f1(p: Path):
    """Return (class_f1, property_f1) from eval_cq_terms_result.json."""
    try:
        d = json.loads(p.read_text())
        m = d["results"]["metrics_overall"]
        return m.get("class_only", {}).get("f1"), m.get("property_only", {}).get("f1")
    except Exception:
        return None, None

def top3_mean_f1(p: Path):
    """CQ2Onto layer json: results is a list of per-method dicts; the leaderboard
    reports the mean of the top-3 f1 values."""
    try:
        d = json.loads(p.read_text())
        f1s = sorted((r.get("f1", 0.0) for r in d.get("results", [])), reverse=True)
        return sum(f1s[:3]) / max(1, len(f1s[:3])) if f1s else None
    except Exception:
        return None

def copytree(src: Path, dst: Path):
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--onto-mode", default="challenge")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--commit", default="")
    args = ap.parse_args()
    root = Path(args.repo_root)
    name = args.name
    dest = root / "submissions" / name / "evaluation"
    if dest.exists():
        shutil.rmtree(dest)           # regenerate cleanly on re-runs
    dest.mkdir(parents=True, exist_ok=True)

    lines = [f"# Evaluation results — {name}", ""]
    stamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines += [f"_Generated {stamp}_" + (f" · commit `{args.commit[:7]}`" if args.commit else ""), ""]

    # CQ2Term
    term_res = root / "CQ2Term" / "03_evaluation_results" / name
    term_sum = root / "CQ2Term" / "04_summary" / name
    if copytree(term_res, dest / "CQ2Term"):
        copytree(term_sum, dest / "CQ2Term" / "_summary")
        lines += ["## CQ2Term (per domain)", ""]
        for dom_dir in sorted(p for p in term_res.iterdir() if p.is_dir()):
            cf, pf = cq2term_f1(dom_dir / "06_cq_terms" / "eval_cq_terms_result.json")
            cs = f"{cf:.3f}" if cf is not None else "?"
            ps = f"{pf:.3f}" if pf is not None else "?"
            lines.append(f"- **{dom_dir.name}** — class F1 {cs}, property F1 {ps}")
        lines.append("")

    # CQ2Onto
    onto_res = root / "CQ2Onto" / "03_evaluation_results" / args.onto_mode / name
    onto_sum = root / "CQ2Onto" / "04_summary" / args.onto_mode / name
    if copytree(onto_res, dest / "CQ2Onto"):
        copytree(onto_sum, dest / "CQ2Onto" / "_summary")
        lines += ["## CQ2Onto (class-layer F1; full layers in folder & _summary)", ""]
        for dom_dir in sorted(p for p in onto_res.iterdir() if p.is_dir()):
            cls = top3_mean_f1(dom_dir / "01_class" / "class_result.json")
            cs = f"{cls:.3f}" if cls is not None else "?"
            lines.append(f"- **{dom_dir.name}** — class F1 {cs}")
        lines.append("")

    (dest / "SUMMARY.md").write_text("\n".join(lines))
    print(f"Wrote evaluation into {dest}")
    print(f"EVAL_DIR={dest}")

if __name__ == "__main__":
    main()
