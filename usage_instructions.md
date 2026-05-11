# How to Use CQ4OE

CQ4OE is an evaluation pipeline. It does not generate ontologies for you. You bring the output from your LLM on one of our 6 domains, and CQ4OE compares it against the CQ-aligned gold standard and produces a Markdown report.

This guide walks you through:

1. installing and choosing which task to evaluate,
2. preparing your prediction files,
3. running the evaluation,
4. reading the report.

---

## 1. Install

Clone the repository and create a fresh Python environment.

```bash
git clone https://github.com/oeg-upm/cq4oe-benchmark.git
cd cq4oe-benchmark

conda create -n cq4oe python=3.10 -y
conda activate cq4oe
pip install -r requirements.txt
```

**Python version.** Tested on **Python 3.10**.

**External dependencies beyond `pip install`:**

- **Java**: needed by `owlready2` for HermiT reasoning in the hierarchy layer (CQ2Onto only). Check with `java -version`. If missing, install any modern JDK.
- **Ollama**: serves the embedding model used for term alignment. Install Ollama, then pull the model once:

  ```bash
  ollama pull embeddinggemma
  ```

  Make sure `ollama serve` is running before you launch the evaluation.

`requirements.txt` covers the Python packages:

```text
rdflib                  # OWL / RDF parsing
owlready2               # HermiT reasoner (CQ2Onto hierarchy)
python-Levenshtein      # edit distance
textdistance            # Jaro-Winkler etc.
sentence-transformers   # embedding similarity
langchain-ollama        # Ollama client
openpyxl                # XLSX export
```

---

## 2. Pick your task

CQ4OE has two evaluation tasks. **Pick one before going further.** The directory you `cd` into, the prediction format, and the runner script are all different.

| Task | What it evaluates | Input you provide | Output |
|---|---|---|---|
| **CQ2Term** | Whether your LLM predicts the **explicit classes and properties** required by each CQ | one JSON file per (model, dataset) listing predicted terms per CQ | term-level P/R/F1 + CQ-conditioned coverage |
| **CQ2Onto** | Whether your LLM produces a **full OWL ontology** that satisfies the CQs | one ontology file per (model, dataset) | five evaluation tasks + CQ-conditioned axiom coverage |

Supported formats for CQ2Onto: `.owl`, `.rdf`, `.xml`, `.ttl`, `.turtle` (anything `rdflib` can parse). The constant in the runner is named `PRED_OWL` for historical reasons but accepts any of these.

Quick rules of thumb:

- Use **CQ2Term** if you only want to test the model's ability to recognize the relevant vocabulary for each CQ.
- Use **CQ2Onto** if you want to grade a complete generated ontology, including property semantics, triples, hierarchy, and axioms.
- You can run **both** on the same model. Just go through each section in turn.

## 3. CQ2Term: term-level evaluation

### 3.1 Folder structure

```
CQ2Term/
├── 00_gold_standard/          ← read-only; per-domain CQ-to-term provenance
│   └── <domain>/
│       ├── cq_to_terms_<domain>.json
│       └── term_to_cqs_<domain>.json
├── 01_predictions/
│   └── <model_name>/          ← any label (e.g. Claude, baseline, default)
│       └── <domain>_terms.json
├── 03_evaluation_results/
├── 04_summary/
├── competency_question/        ← raw CQs per domain
└── scripts/
    ├── concept_label_matching.py
    ├── eval_cq_terms.py
    └── run_all_cq2term.py
```

The six available domains are: `wine`, `awo`, `odrl`, `water`, `vgo`, `swo`.

### 3.2 Generate predictions

For each model and each domain you want to evaluate:

1. Read the CQs from `competency_question/<domain>_cqs.json`.
2. For each CQ, predict the required classes and properties with your LLM.
3. Save as JSON in the same format as `00_gold_standard/<domain>/cq_to_terms_<domain>.json`.

Place predictions one folder per model:

```
01_predictions/
└── my_model/                  ← any name; used as the label in reports
    ├── wine_terms.json
    ├── awo_terms.json
    ├── odrl_terms.json
    ├── water_terms.json
    ├── vgo_terms.json
    └── swo_terms.json
```

The `<model_name>` folder works as a label. Use any name like `Claude`, `baseline`, or `default`. This name becomes the directory under `03_evaluation_results/` and `04_summary/`. The folder layer is required. JSON files placed directly under `01_predictions/` will not be picked up.

### 3.3 Configure and run

Open `CQ2Term/scripts/run_all_cq2term.py` and edit one constant at the top:

```python
PYTHON = "/path/to/your/python"   # run `which python` inside your cq4oe env
```

Then run from the `CQ2Term/` directory:

```bash
cd CQ2Term
python -u scripts/run_all_cq2term.py
```

The runner scans each folder under `01_predictions/` and pairs it with each domain in `DATASETS = ["wine", "vgo", "swo", "awo", "odrl", "water"]`. It runs `eval_cq_terms.py` when both files exist, and prints SKIP otherwise. No per-run edits needed. Drop your model folder into `01_predictions/` and the runner picks it up.

### 3.4 Inspect the outputs

After a run, each (model, dataset) pair produces:

```
03_evaluation_results/<model>/<dataset>/06_cq_terms/
├── eval_cq_terms_result.json          ← P/R/F1 summary
├── cqterm_class_best_matching.csv     ← accepted class alignment
├── cqterm_prop_best_matching.csv      ← accepted property alignment
├── cqterm_class_trace.csv             ← per-method similarity scores (classes)
├── cqterm_prop_trace.csv              ← per-method similarity scores (properties)
├── cq_coverage.csv                    ← per-CQ coverage (At-least-one / Mean / Full)
└── term_coverage.csv                  ← per-term coverage

04_summary/<model>/<dataset>_report.md ← read this first
```

### 3.5 Run a single (model, dataset) pair

Call `eval_cq_terms.py` directly when you want to rerun one pair without invoking the full runner. Useful for debugging or for adjusting parameters like the similarity threshold.

The dataset name (`wine` in the example below) lives in the file paths. To switch to a different dataset, replace `wine` with `awo`, `odrl`, `water`, `vgo`, or `swo`.

```bash
cd CQ2Term
python scripts/eval_cq_terms.py \
  --gold_cq_to_terms 00_gold_standard/wine/cq_to_terms_wine.json \
  --pred_cq_to_terms 01_predictions/my_model/wine_terms.json \
  --final_threshold 0.6 \
  --save_result_json 03_evaluation_results/my_model/wine/06_cq_terms/eval_cq_terms_result.json \
  --save_report_md   04_summary/my_model/wine_report.md
```

---

## 4. CQ2Onto: full-ontology evaluation

### 4.1 Folder structure

```
CQ2Onto/
├── 00_gold_standard/           ← read-only
│   └── <domain>/
│       ├── ontology/sub_<domain>.owl         ← CQ-aligned gold ontology
│       └── axioms/<domain>_axiom_gold.json   ← TBox axioms with CQ provenance
├── 01_predictions/             ← drop your generated ontology files here
├── 02_atomic_axioms/           ← intermediate axiom decomposition
├── 03_evaluation_results/      ← per-layer raw scores (CSV / JSON)
├── 04_summary/                 ← Markdown reports
├── competency_question/        ← raw CQs per domain
├── prompts/                    ← prompts used in the paper (cqbycq, MASEO)
└── scripts/
    ├── concept/eval_concept.py
    ├── property/eval_property.py
    ├── triple/eval_triple.py
    ├── axioms/Axioms_atomic.py
    ├── axioms/eval_axioms.py
    ├── hierarchy/eval_hierarchy.py
    └── run_all_evaluation_agent_4datsets.py
```

### 4.2 Choose your scope

You decide how many domains to test, from one to all six. The runner evaluates **one (prediction, domain) pair per run**.

- One domain: produce one ontology file, run the script once. One report.
- Multiple domains: produce one ontology file for each. Run the script once for each, editing `PRED_OWL` and `DATASET` between runs. One report per domain.

Supported formats: `.owl`, `.rdf`, `.xml`, `.ttl`, `.turtle` (anything `rdflib` can parse). The constant in the runner is named `PRED_OWL` for historical reasons but accepts any of these.

Partial benchmarks are valid (e.g. Wine + AWO only). Just report which domains you ran. To match the numbers in the CQ4OE paper, run all six.

Common situations:

- Testing a prompt change on one domain: one file, one run.
- Comparing two prompting strategies on Wine: two files, two runs.
- Full benchmark on a new LLM: six files, six runs.

### 4.3 Generate predictions

For each domain you want to evaluate:

1. Read the CQs from `CQ2Onto/competency_question/<domain>_cqs.json` (some domains use `<domain>_cq2onto_cqs.json`).
2. Feed them to your LLM under any generation strategy (one-shot, CQ-by-CQ, multi-agent, …). Prompts used in the paper are under `CQ2Onto/prompts/` if you want to reproduce them.
3. Save the result as one ontology file per domain (`.owl`, `.rdf`, `.xml`, `.ttl`, or `.turtle`).

Drop the file into `01_predictions/`. Naming is up to you. A convention like `<ModelName>_<domain>.owl` keeps multiple runs distinguishable.

```
01_predictions/
└── Claude_wine.owl
```

### 4.4 Configure the runner

Open `scripts/run_all_evaluation_agent_4datsets.py` and edit the three constants at the top.

```python
PYTHON   = "/path/to/your/python"
PRED_OWL = Path("01_predictions/Claude_wine.owl")
DATASET  = "wine"
```

| Constant | What to put | Notes |
|---|---|---|
| `PYTHON` | absolute path to the Python in your `cq4oe` env | run `which python` inside the env |
| `PRED_OWL` | path to your ontology file, relative to `CQ2Onto/` | must exist; any `rdflib`-readable format |
| `DATASET` | one of `wine`, `awo`, `odrl`, `water`, `vgo`, `swo` | must match the domain your ontology was generated for |

> The script evaluates **one (prediction, domain) pair per run**. For multi-domain evaluation, edit these constants and re-run.

### 4.5 Run the evaluation

From the `CQ2Onto/` directory.

```bash
cd CQ2Onto
python -u scripts/run_all_evaluation_agent_4datsets.py
```

The script runs five evaluation layers in order.

1. **Concept** (`scripts/concept/eval_concept.py`). Class alignment and recovery.
2. **Property** (`scripts/property/eval_property.py`). Property alignment and recovery.
3. **Triple** (`scripts/triple/eval_triple.py`). Domain / range triple match.
4. **Axioms** (`scripts/axioms/Axioms_atomic.py`, then `scripts/axioms/eval_axioms.py`). The first decomposes your prediction into atomic TBox axioms. The second compares them to the gold axioms with CQ provenance.
5. **Hierarchy** (`scripts/hierarchy/eval_hierarchy.py`). Reasoner-based closure recovery (needs Java).

If any layer fails the script stops. A successful run means all five layers completed.

### 4.6 Run individual layers

The five layers are independent scripts and can be run on their own. Useful for debugging or for re-running one part without redoing the whole pipeline.

**Hard dependency.** The last three layers (`triple`, `axioms`, `hierarchy`) require the alignment CSVs produced by `concept` and `property`. Required order:

1. `concept` (produces `class_best_matching.csv`)
2. `property` (produces `property_best_matching.csv`)
3. `triple`, `axioms`, `hierarchy` (all three read the two CSVs above)

After `concept` and `property` finish you have:

```
03_evaluation_results/single/<dataset>/01_class/class_best_matching.csv
03_evaluation_results/single/<dataset>/02_property/property_best_matching.csv
```

These two CSVs are read by the later layers through `--class_csv` and `--property_csv`.

**Example.** Run only the triple layer on Wine, assuming concept and property already ran.

```bash
python scripts/triple/eval_triple.py \
  --pred_onto 01_predictions/Claude_wine.owl \
  --gold_onto 00_gold_standard/wine/ontology/sub_wine.owl \
  --class_csv    03_evaluation_results/single/wine/01_class/class_best_matching.csv \
  --property_csv 03_evaluation_results/single/wine/02_property/property_best_matching.csv \
  --save_result      03_evaluation_results/single/wine/03_triple/triple_result.json \
  --save_layer3_csv  03_evaluation_results/single/wine/03_triple/triple_layer3_pairs.csv \
  --save_layer3_json 03_evaluation_results/single/wine/03_triple/triple_layer3_pairs.json \
  --save_report_md   04_summary/single/wine_report.md
```

The CLI flags for each layer are the ones the runner passes. Open `run_all_evaluation_agent_4datsets.py` and copy the relevant `run([...])` block.

**Skipping concept or property is not allowed.** Running any of `triple` / `axioms` / `hierarchy` without those two CSVs will fail.

### 4.7 Inspect the outputs

After a successful run on `wine`, the outputs land under three top-level directories. The `single/` segment is the `model` label (hard-coded to `"single"` in the runner). Change it to keep different models apart.

```
02_atomic_axioms/single/wine/
  └── Claude_wine_atomic_tbox.json        ← your prediction in atomic-TBox form

03_evaluation_results/single/wine/
  ├── 01_class/
  ├── 02_property/
  ├── 03_triple/
  ├── 04_axiom/
  │   └── strict_cq_coverage.csv          ← per-CQ axiom recovery
  └── 05_hierarchy/

04_summary/single/wine_report.md          ← read this first
```

**Read `04_summary/single/wine_report.md` first.** It aggregates all five layers in one place, with per-CQ traces of what was matched, what was missed, and what was rescued through reasoning.

---

## 5. Read the gold standards directly (no evaluation)

If you only want to inspect the requirements, skip the runner and go straight to the gold files.

**CQ2Term.** `CQ2Term/00_gold_standard/<domain>/cq_to_terms_<domain>.json` records the CQ-to-term provenance. For each CQ you get the explicit classes and properties required to answer it.

**CQ2Onto.** `CQ2Onto/00_gold_standard/<domain>/` contains:

- `ontology/sub_<domain>.owl`: the CQ-aligned sub-ontology produced by Phase 4 of the annotation pipeline.
- `axioms/<domain>_axiom_gold.json`: TBox axioms with CQ-to-axiom provenance.

These are exactly what the evaluation pipeline compares against. Anything you read here is what your model is graded on.

---

## 6. Interpret the metrics

Each layer reports **TP, FP, FN, Precision, Recall, and F1**. The Markdown report shows them all. F1 is the headline number used for cross-layer comparison, but Precision and Recall are equally available and often more informative (a low Precision with high Recall means the model over-generates; the opposite means it is too conservative).

The metric names match those used in the CQ4OE paper.

**Term-level (Class, Property).** P/R/F1 between gold and predicted terms after one-to-one alignment. The alignment aggregates five similarity methods (`hard_match`, `sequence_match`, `levenshtein`, `jaro_winkler`, `semantic`), keeping the top-3 mean. Thresholds default to `0.6` for classes and `0.7` for properties.

**Property characteristics** *(CQ2Onto only)*. P/R/F1 over OWL property flags (functional, inverse, transitive, …) on aligned properties.

**Domain / range triples** *(CQ2Onto only)*. P/R/F1 over `(subject, predicate, object)` triples derived from `rdfs:domain` / `rdfs:range`.

**TBox axioms** *(CQ2Onto only)*. P/R/F1 over strictly matched TBox axioms after recursively translating terms through the alignment.

**Hierarchy closure** *(CQ2Onto only)*. P/R/F1 over inferred class and property subsumptions, capturing hierarchy that is entailed rather than explicitly asserted.

**Two views, Global vs Alignment-Conditioned (AC)** *(CQ2Onto only)*.

- *Global*: over the entire gold and predicted sets. Penalises both wrong vocabulary and wrong structure.
- *AC*: restricted to elements whose terms successfully aligned. Isolates structural mistakes from vocabulary mistakes.

A large gap between AC and Global means the model knows the structure but uses the wrong labels (or vice versa).

**CQ-conditioned coverage.** Three numbers per CQ-level target.

- *At-least-one*: share of CQs with ≥ 1 required item recovered.
- *Mean*: average per-CQ recovery.
- *Full*: share of CQs whose required items are *all* recovered.

For axioms (CQ2Onto), this is reported twice: before closure rescue (`Axioms-…`) and after closure rescue (`Closure-…`). The gain `Δ = Closure-Mean − Axioms-Mean` tells you how much of the missed axiom requirement is rescued by reasoning over the predicted hierarchy.

---
