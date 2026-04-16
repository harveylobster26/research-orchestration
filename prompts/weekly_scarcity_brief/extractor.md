You are extracting weekly scarcity-stack investment signals from a single source document.

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
- Capture explicit quotes, named partners, shortages, capex commitments, and forward-looking supply chain language.
- Preserve macro regime signals when the document is about energy, inflation, rates, or credit stress.
- Reject material that does not clearly advance transcript, macro, or supply chain signal extraction.
