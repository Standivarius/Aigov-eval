# AIGov-eval Dictionary (Glossary)

This glossary defines terms used across:
- **aigov-eval** (evaluation engine + harness)
- **aigov-eval-specs** (schemas, definitions, acceptance criteria)
- **aigov-eval-mvp** (product wrapper / minimal UI / integration surface)

If a term conflicts between repos, the definition in **aigov-eval-specs** is authoritative.

---

## Repositories

- **aigov-eval**  
  Python evaluation engine: targets, runner, scoring/judge, batch calibration harness.

- **aigov-eval-specs**  
  Normative definitions: case schema, signal taxonomy, metric definitions, reporting requirements.

- **aigov-eval-mvp**  
  Minimal product integration surface. Should not redefine core semantics.

---

## Core objects

- **Case (Calibration Case)**  
  A single test input for batch calibration, typically stored as JSON. Includes scenario prompt/context plus expectations for verdict and signals.

- **Scenario**  
  A runnable conversational script or interaction definition. In this repo, `run` typically executes a single scenario; `batch-run` iterates across many cases.

- **Transcript-first evaluation**  
  Principle: record the full interaction (transcript + evidence) and score afterwards. Makes re-scoring deterministic given identical artefacts.

- **Evidence pack**  
  Audit artefact capturing raw inputs/outputs sufficient to reconstruct and defend a result (transcript, signals/verdict, configuration, optional target/judge traces).

---

## Execution modes

- **run (CLI subcommand)**  
  Executes one scenario against a target. Produces per-run artefacts.

- **batch-run (CLI subcommand)**  
  Executes a set of calibration cases (often with repeats). Produces:
  - `runs/batch_<id>/batch_summary.json`
  - `runs/batch_<id>/batch_report.md`
  - per-case per-repeat run directories with full artefacts

- **Repeat**  
  Running the same case N times to measure stability (verdict repeatability, modal signals, etc.).

---

## Targets (systems under test)

- **Target adapter**  
  A concrete implementation that receives messages and returns assistant outputs for evaluation.

- **TARGETS registry**  
  The set of available target adapters exposed by CLI `--target`.

- **scripted (target)**  
  Deterministic Python target. Useful as a baseline and for CI.

- **mock-llm (target)**  
  LLM-backed target adapter (OpenRouter/OpenAI-compatible). Uses env vars like:
  - `OPENROUTER_API_KEY` (required)
  - `OPENROUTER_MODEL` (optional, default exists)
  - `OPENROUTER_BASE_URL` (optional)

- **http (target)**  
  External HTTP service target. Used later for real system integration.

- **sim-chatbot (planned target concept)**  
  *Not the same as mock-llm.*  
  A target that prompts an LLM to roleplay as the audited chatbot (e.g., medical services customer support),
  and emits an internal “intent/disclosure log” for comparison against the judge output.

---

## Judge and scoring

- **Judge**  
  Component that produces:
  - a **verdict** (PASS/FAIL/UNCLEAR) and/or
  - a set of extracted **signals**.
  Judge may be rule-based, LLM-based, or hybrid.

- **mock_judge**  
  A deterministic judge mode used to validate harness wiring and compute expected metrics without external dependencies.

- **Live judge**  
  Judge mode that uses the real judge implementation (may call an LLM or a non-deterministic component).

---

## Verdicts and signals

- **Verdict**  
  Outcome classification per case/run:
  - PASS: compliant behaviour
  - FAIL: violation detected
  - UNCLEAR: insufficient evidence or judge abstention

- **Signal**  
  A discrete, named indicator of a compliance issue (e.g., lack of consent, special category disclosure).
  Signal names should come from the project taxonomy (e.g., `taxonomy/signals.json` if present).

- **required_signals**  
  The minimum set of signals that MUST be present for the run to count as correct.

- **allowed_extra_signals**  
  Signals that may appear without penalty (used to avoid over-penalising legitimate secondary findings).

- **Expected signals**  
  A case’s required + allowed signals specification. Not necessarily exhaustive.

- **Observed signals**  
  Signals emitted by the judge for a specific run.

- **Modal signals**  
  Signals most frequently observed across repeats for the same case (used for stability metrics).

---

## Metrics (batch calibration)

- **verdict_repeatability**  
  Percent of repeats that produced the same verdict.

- **verdict_accuracy**  
  Whether the observed verdict matches expected verdict (or policy-defined correctness condition).

- **signals_strict_accuracy**  
  Observed signals must match expected signals exactly (typically too strict for non-exhaustive expectations).

- **signals_subset_accuracy**  
  Observed signals must be a subset of expected allowed set (or other subset rule).

- **required_recall_accuracy**  
  Whether all required signals were present (primary metric when expectations are non-exhaustive).

- **allowed_only_accuracy**  
  Whether any extra signals are within the allowed set (penalises hallucinated/unapproved signals).

---

## Artefacts

- **runs/**  
  Output directory containing run artefacts. Typically not committed to git to avoid repo bloat.

- **Run directory**  
  A single execution’s artefacts, typically including:
  - transcript
  - scores/verdict
  - evidence pack
  - run metadata (git sha, configuration)

- **Batch directory**  
  `runs/batch_<id>/` containing batch-level report + per-case run dirs.

---

## Operational conventions

- **Reproducibility requirement**  
  Artefacts must include enough metadata to rerun or explain results:
  git sha, target, judge mode, model identifiers (if used), seed/temperature, and any cost/latency fields if available.

- **Orchestration is lightweight**  
  Prefer simple CLI invocations and simple file artefacts over complex pipelines, as long as evidence remains audit-grade.
