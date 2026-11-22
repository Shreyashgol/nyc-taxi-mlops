# 015: Chunk size 250 tokens, overlap 40 tokens, and top-k 3

Stage: S6 · Date: 2026-11-22 · Author: Shreyash · Drafted by agent: yes

## Choice

Split wiki pages into markdown chunks with a target maximum of 250 tokens (~190 words) and an overlap of 40 tokens (~30 words) between consecutive pieces within the same section. In retrieval (`POST /assist`), return the top-3 chunks (`top_k = 3`) ordered by cosine similarity.

## Rejected alternative

We considered smaller chunks (e.g. 100 tokens) with top-k = 5, or larger chunks (500 tokens) with top-k = 1.
- Very small chunks lose essential context across sentences or list items (e.g., fee definitions or exceptions).
- Larger chunks or higher top-k substantially increase the prompt length. On CPU execution with llama.cpp, every chunk costs ~11 seconds of prompt evaluation; sending 5+ chunks would push response times past 60–90 seconds per query.

## Why

Ops wiki pages are concise and cleanly split into markdown headings.
1. `max_tokens = 250` covers complete policy rules and tables without arbitrary mid-sentence cuts.
2. `overlap_tokens = 40` ensures sentences spanning chunk boundaries remain searchable.
3. `top_k = 3` provides sufficient multi-document context while keeping prompt evaluation time under ~35 seconds on Graviton CPUs.

## What would show this was wrong

If evaluation on complex multi-policy questions fails due to missing context (low recall), or if prompt processing time routinely causes timeouts (exceeding 60 seconds), we should adjust chunk bounds or top-k accordingly.
