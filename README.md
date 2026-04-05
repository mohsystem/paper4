# Paper 4: Developer Security Training Study

This repository contains the source code, analysis scripts, data artifacts, and supplementary materials for a controlled developer study on the effectiveness of security training in improving the security quality of LLM-assisted backend development.

The study is instantiated in an identity-centric Java Spring Boot backend and evaluates submitted implementations through independent dual-reviewer manual validation.

## Repository Structure

- `Appendix/`: Supplementary documents and detailed specifications.
  - `appendix_task_set_specifications.md`: Functional requirements for the task sets used in the study.
  - `appendix_participant_severity_profiles.md`: Raw severity counts per participant.
  - `appendix_security_findings_examples.md`: Representative validated security findings with code snippets and mitigation notes.
  - `appendix_quantitative_results_summary.md`: Summary of quantitative results, including overall totals, paired outcomes, and descriptive weakness-family shifts.
- `src/`: Source code for the study environment and analysis.
  - `analysis/`: Scripts for processing findings, validating reported numbers, and generating statistics and figures.
  - `llm_integration/`: Integration modules for LLM providers such as OpenAI, Claude, and Gemini.
  - `app_developer_env_new.py`: Flask-based UI for the developer task environment used in the study.
- `cwes_ds/`: Dataset of enriched CWE information used to support analysis and descriptive mapping.

## What This Repository Includes

This repository supports the full study workflow, including:

- the manuscript source
- validated security review outputs
- participant-level analysis artifacts
- descriptive and inferential summary scripts
- appendix materials and representative findings
- the developer task environment used in the experiment

## Main Study Result

Under the tested conditions, the post-training condition produced a lower validated security burden than the pre-training condition.

Key aggregate outcomes:

- validated weaknesses decreased from **162** to **111** (**31.5%**)
- aggregate severity-weighted burden decreased from **432** to **267** (**38.2%**)
- critical findings decreased from **24** to **5** (**79.2%**)

The clearest descriptive gains were observed in authorization and object access, and in authentication, credential policy, and recovery. More persistent issues remained in session and browser trust-boundary weaknesses, some cryptographic implementation problems, and abuse-resistance or operational hardening concerns.

## Usage

### Analysis

To run the core analysis and regenerate the summary statistics:

```powershell
python src/analysis/validate_numbers_v2.py
python src/analysis/theme_mapping/generate_theme_mapping_and_shifts.py
```

### Developer Environment

To launch the developer environment UI:

```powershell
python src/app_developer_env_new.py
```

The UI will be available at `http://localhost:5000`.

## Requirements

- Python 3.10+
- Flask
- OpenAI
- Pandas
- SciPy
- Statsmodels

## Scope of the Findings

The study was conducted in a specific setting: an identity-centric Java Spring Boot backend under a fixed LLM-assisted development workflow. The findings should therefore be interpreted as evidence under the tested conditions rather than as a universal claim about all developers, all models, or all software domains.

## License

The source code in this repository is licensed under the MIT License unless stated otherwise.  
The manuscript text, appendix materials, figures, and data artifacts remain the intellectual property of the authors and should not be redistributed or reused without permission.