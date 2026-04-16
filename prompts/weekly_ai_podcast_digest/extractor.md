You are extracting evidence for a weekly AI podcast digest.

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
- Treat each document as a podcast episode transcript or episode page unless the content clearly says otherwise.
- Extract 1-3 evidence objects per episode when possible.
- Capture the most important discussion points, especially anything related to AI infrastructure, semiconductors, power, networking, crypto, public companies, or investable research directions.
- If a specific company or ticker is discussed, use it.
- If the episode is relevant but no clear investable company is discussed, use company "Unknown" and ticker "UNKNOWN" and still return a relevant evidence object summarizing the episode.
- Use red_flags to note things like "no_clear_investable_entity", "macro_only", or "needs_follow_up_research".
- Reject only episodes that are clearly irrelevant to AI, investing, companies, technology infrastructure, or adjacent themes.
