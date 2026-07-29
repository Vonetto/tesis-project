# Project Agent Instructions

## Relevant Prompt Tracking

This repository keeps an audit trail of structurally important AI prompts in:

- `docs/ai_usage/prompt_history.sqlite3`
- `docs/ai_usage/prompt_history.jsonl`

At the start of every new session in this repository, run:

```bash
python scripts/ai_usage_log.py list --limit 5
```

Use this only to recover the recent audit trail. Do not infer that unrecorded
conversation was irrelevant.

Before the final response to each user turn, decide whether the prompt is relevant
under `docs/ai_usage/README.md`.

Record it when it changes or establishes at least one of:

- project objective, scope, assumptions, methodology, or decision;
- data construction, audit, modeling, implementation, or debugging work;
- a reproducibility, documentation, governance, or workflow rule;
- approval or rejection of a concrete substantive alternative.

Do not record:

- acknowledgements such as `ok`, `me parece`, or `gracias`;
- requests to continue that introduce no new decision;
- casual conversation or wording/style adjustments;
- pasted outputs without a new analytical or methodological request;
- secrets, credentials, or unnecessary personal information.

If a short prompt contains a substantive instruction, such as
`ok, construyamos la demanda por modo`, record the substantive prompt.

After completing the turn, log one entry with the exact decision-bearing part of
the user prompt and a concise description of how AI was used:

```bash
python scripts/ai_usage_log.py record \
  --category <category> \
  --prompt "<decision-bearing user prompt>" \
  --summary "<short prompt summary>" \
  --relevance-reason "<why this belongs in the audit trail>" \
  --requested-outcome "<what the user requested>" \
  --ai-use-summary "<analysis/actions performed by AI>" \
  --status completed \
  --artifact <path> \
  --tool <tool-name> \
  --tag <tag>
```

For large pasted tables or attachments, store only the instruction-bearing text
and add the source path or label with `--input-ref`. Never copy large raw data into
the prompt database.

Verify the latest record when logging fails or is uncertain:

```bash
python scripts/ai_usage_log.py list --limit 5
```

At the end of a multi-turn workstream or before a commit/handoff, compare the
structural decisions in the task plan and notes against the recent prompt history.
Backfill missing entries with `--status completed` or `--status partial` and note
that they were reconstructed. This reconciliation is a safeguard, not a substitute
for per-turn logging.
