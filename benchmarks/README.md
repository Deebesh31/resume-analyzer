# Resume analysis benchmarks

## Included: Structure score rubric regression

`structure_score_cases.json` is a small, synthetic regression dataset for the deterministic 100-point Structure score. It covers complete and sparse resumes, early-career content, missing parser signals, low extraction quality, the quality-band fallback, and measurable achievement evidence. The source text and parser profiles are fictional; no candidate documents or third-party resume data are stored here.

Run it from the repository root after installing the app's requirements. This local check makes no API calls and needs no Affinda or OpenAI key:

```powershell
.\.venv\Scripts\python.exe benchmarks\run_structure_score_benchmark.py
```

The runner compares every case's total and per-factor points with its expected values. It reports exact-score agreement and mean absolute error (MAE) on the 0–100 scale, plus per-factor MAE. A mismatch exits with status 1.

These expected values are derived from the same documented rubric as the implementation. A passing run proves that code changes preserve those rules; it does not validate the weights against recruiter judgment, a particular employer's ATS, interviews, or hiring outcomes. Do not present it as predictive validation.

## External parser benchmark: Careerflow ResumeBench

[Careerflow ResumeBench](https://github.com/careerflow/ResumeBench) is a closer fit for measuring parser extraction accuracy. Its reference records cover 14 structured resume sections; its deterministic scorer compares extracted fields to human-checked references and penalizes omissions and extractions that are not in the source. It reports field precision, recall, and F1. The Hugging Face listing describes a 20-document public split and a 300-document full set, and currently requires users to review and accept access conditions before downloading files. The dataset is marked CC BY 4.0 there; the evaluation framework repository is Apache-2.0.

The CV files are not copied into this repository. To run the external benchmark, first review the dataset conditions and obtain access in Hugging Face, then follow Careerflow's download and scoring instructions. Its README documents how to add a custom provider and how to grade a predictions JSONL file. An Affinda adapter would need to map Affinda's parsed fields to ResumeBench's 14-section schema. Parsing each document sends it to Affinda and consumes parser credits, so the benchmark should only be run with an Affinda key and after reviewing the test-document and service data terms.

The [EMNLP 2025 ResumeBench from ApplyU](https://github.com/ApplyU-ai/ResumeBench) is a separate project despite sharing the name. Its dataset is licensed CC BY-NC 4.0 and access is by request; it is not bundled here for a public product repository.

## Validating the feedback and score as advice

There is no universal ATS score to use as a gold label. ATS products and employer configurations differ, and the Structure score measures a narrow rubric rather than the chance of getting hired. Research comparing LLM resume-match scores with human ratings found only minor correlation, which is a reason to test against independent people rather than assume that a model's number is ground truth ([Vaishampayan et al., Findings of NAACL 2025](https://aclanthology.org/2025.findings-naacl.270/)).

To test whether the score reflects useful resume advice, the next dataset should be built from opt-in, de-identified documents, with two independent reviewers applying a published rubric for completeness, clarity, skills, achievements, language, consistency, and overall impact. Keep both ratings, report reviewer agreement, and compare the product's components and recommendations with reviewer judgments. ResumeGenAI's small user study is one example of expert-rated, multidimensional pre/post evaluation, rather than treating a parser benchmark as an advice-quality benchmark ([Awasthi et al., CUI 2025](https://doi.org/10.1145/3719160.3737622)).
