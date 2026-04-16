You are extracting evidence for an AI Infrastructure Early Discovery Brief.

Return JSON only with this schema:
{
  "evidence": [
    {
      "company": "string",
      "ticker": "string",
      "bottleneck_category": "string",
      "source_url": "string",
      "source_type": "string",
      "evidence_summary": "string",
      "evidence_snippet": "string",
      "ai_infra_relevance": 0.0,
      "underfollowed_signal": 0.0,
      "rerated_risk": 0.0,
      "confidence": 0.0,
      "red_flags": ["string"],
      "is_relevant": true,
      "rejection_reason": null
    }
  ]
}

Rules:
- Prefer primary-source and trade-press evidence that speaks to real bottlenecks, lead times, backlog, qualification, named partners, and demand inflection.
- Anchor evidence to a physical layer whenever possible.
- Penalize names that look obvious, crowded, or already fully rerated.
- Reject weak thematic mentions explicitly.
