# Trace/Spans vs Audit Log

A quick-reference comparison before the answers:

| Axis | Trace / Spans | Audit log |
|---|---|---|
| Question | How did it run? Where's the time? | Who did what? Prove it. |
| Completeness | Sampled — keep ~10% | Every record — never sampled |
| Mutability | Expires, can be dropped | Append-only, tamper-evident |
| Lifetime | Hours → weeks | Months → years (WORM) |
| Audience | SRE, devs, FinOps | Compliance, legal, security |
| Built from | OpenTelemetry spans | Signed / hash-chained sink |

---

## Case 1
**"You're reproducing a single failing request in staging — show the full call tree and pinpoint where it errored."**

### Answer: Trace / Spans

**Justification:** This is fundamentally a "how did it run, where's the time, where did it break" question — exactly what the comparison table lists as the Trace/Spans axis. You need the *full call tree* (the hierarchical request → retrieval → underwrite → model.call → guardrail structure), with per-span timing, to visually pinpoint exactly which span failed. An audit log only gives discrete "what happened" decision records — it has no concept of a call tree or duration, so it can't show nesting or latency. This is a debugging task for SRE/engineers, which matches the Trace/Spans audience.

---

## Case 2
**"FinOps wants average cost & tokens per request on a live dashboard. Sampling 10% is fine with them."**

### Answer: Trace / Spans

**Justification:** Two details lock this in: (1) they explicitly say *sampling 10% is fine* — sampling is a defining property of traces ("Sampled — keep ~10%"), while audit logs must never be sampled since they need to be complete for compliance. (2) Cost/token-per-request is per-span metadata naturally attached to `model.call` spans, and a "live dashboard" implies short-lived, aggregate operational metrics — not a permanent legal record. FinOps is an operational/SRE-style audience, not compliance/legal.

---

## Case 3
**"This decision record must survive even a DBA with write access trying to alter it three years from now."**

### Answer: Audit log

**Justification:** The key phrase is "survive... write access... alter it" — this demands **tamper-evidence**, which only the audit log provides via its append-only, hash-chained structure (each entry stores `prev: sha256:...` linking to the previous record, so any alteration breaks the chain and is detectable — "chain verified · 0 gaps"). Traces are mutable and expire in hours-to-weeks; they're not designed to resist tampering or to persist "three years from now." The audit log's lifetime (months → years, WORM) and its security/compliance audience are exactly what this ticket needs.

---

## Case 4
**"A guardrail blocked a suspicious transaction. Compliance needs a permanent record that it was blocked; on-call needs to debug why it fired on a legit-looking request."**

### Answer: Both

**Justification:** This ticket explicitly splits into two distinct needs that map to the two different tools:
- **Compliance needs a *permanent record*** → that's the Audit log's job (immutable, hash-chained `guardrail.passed`/blocked decision record that proves the block happened and can't be disputed later).
- **On-call needs to *debug why it fired*** → that's the Trace/Spans job (walking the `guardrail` span's timing and context within the full request tree to understand the runtime conditions that triggered it).

Since one audience needs proof-of-decision and the other needs runtime diagnostics, and the two systems are linked by a shared `trace_id`, you need **both** — you'd pull the audit entry for compliance and pivot to the trace via the linked ID for the on-call investigation.

---

