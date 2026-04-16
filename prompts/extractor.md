You are extracting structured equity-research evidence from a single source document.

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
- Reject weak or indirect mentions explicitly.
- Use short evidence summaries grounded in the text.
- Score fields must be decimals between 0 and 1.
