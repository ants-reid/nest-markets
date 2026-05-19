"use client";

import { useState } from "react";
import { applyPromptAdaptation } from "../../lib/api";
import styles from "../../styles/pages/prompt-adaptations.module.css";

interface ProposalForm {
  setup_type: string;
  rationale: string;
  proposed_prompt_text: string;
  current_win_rate: number;
  total_samples: number;
}

const EMPTY_FORM: ProposalForm = {
  setup_type: "",
  rationale: "",
  proposed_prompt_text: "",
  current_win_rate: 0,
  total_samples: 0,
};

export default function PromptAdaptationsPage() {
  const [form, setForm] = useState<ProposalForm>(EMPTY_FORM);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function handleChange(key: keyof ProposalForm, value: string | number) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleApply() {
    setSubmitting(true);
    setError(null);
    setResult(null);
    try {
      const data = await applyPromptAdaptation(form);
      setResult(`Created PromptVersion v${data.version} (id: ${data.id}) — inactive, ready for review.`);
      setForm(EMPTY_FORM);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to apply adaptation.");
    } finally {
      setSubmitting(false);
    }
  }

  const isValid =
    form.setup_type.trim().length > 0 &&
    form.rationale.trim().length > 0 &&
    form.proposed_prompt_text.trim().length > 0 &&
    form.current_win_rate >= 0 &&
    form.total_samples >= 0;

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>Prompt Adaptations</h1>
      <p className={styles.subtitle}>
        Apply an AI-proposed prompt revision for an underperforming setup type. A new PromptVersion
        row will be created (inactive) for operator review.
      </p>

      <div className={styles.container}>
        <label className={styles.label}>Setup Type</label>
        <input
          className={styles.input}
          placeholder="e.g. BREAKDOWN_FADE"
          value={form.setup_type}
          onChange={(e) => handleChange("setup_type", e.target.value)}
        />

        <label className={styles.label}>Current Win Rate (0 – 1)</label>
        <input
          className={styles.input}
          type="number"
          step="0.01"
          min="0"
          max="1"
          value={form.current_win_rate}
          onChange={(e) => handleChange("current_win_rate", parseFloat(e.target.value) || 0)}
        />

        <label className={styles.label}>Total Samples</label>
        <input
          className={styles.input}
          type="number"
          min="0"
          value={form.total_samples}
          onChange={(e) => handleChange("total_samples", parseInt(e.target.value, 10) || 0)}
        />

        <label className={styles.label}>Rationale</label>
        <textarea
          className={styles.textarea}
          placeholder="Explain why this prompt needs updating..."
          value={form.rationale}
          onChange={(e) => handleChange("rationale", e.target.value)}
        />

        <label className={styles.label}>Proposed Prompt Text</label>
        <textarea
          className={styles.monoTextarea}
          placeholder="Paste the revised prompt section here..."
          value={form.proposed_prompt_text}
          onChange={(e) => handleChange("proposed_prompt_text", e.target.value)}
        />

        <button
          type="button"
          disabled={!isValid || submitting}
          onClick={() => void handleApply()}
          className={styles.submitButton}
        >
          {submitting ? "Applying…" : "Apply Adaptation"}
        </button>

        {result && <p className={styles.successMsg}>{result}</p>}
        {error && <p className={styles.errorMsg}>{error}</p>}
      </div>
    </div>
  );
}
