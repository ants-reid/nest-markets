"use client";

// MH-COCKPIT-03 — Market cockpit mode selector.
//
// Operator-facing cockpit surface that shows the current operating mode,
// explains the allowed paper-only behaviour, and keeps live modes visible but
// locked. Backend guards remain authoritative.

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getAutoPaperStatusCard,
  type AutoPaperStatusCard,
} from "../../lib/api/cockpitAutoPaperStatus";
import {
  getCockpitMode,
  updateCockpitMode,
  type CockpitModeId,
  type CockpitModeResponse,
} from "../../lib/api/cockpitMode";
import styles from "../../styles/pages/cockpit-hub.module.css";

interface CockpitLink {
  href: string;
  title: string;
  description: string;
}

const SECTIONS: ReadonlyArray<{
  heading: string;
  items: ReadonlyArray<CockpitLink>;
}> = [
  {
    heading: "Operator overviews",
    items: [
      {
        href: "/cockpit/eod-report",
        title: "End-of-Day report",
        description:
          "Paper-only end-of-day recap covering opens, closes, incidents, and lessons without any trading actions.",
      },
      {
        href: "/cockpit/notifications",
        title: "Notifications digest",
        description:
          "Compact, severity-filtered digest of recent operator-relevant notifications.",
      },
      {
        href: "/cockpit/auto-paper-status",
        title: "Auto-paper status",
        description:
          "Read-only view of auto-paper enforcement state. Enforcement remains OFF.",
      },
      {
        href: "/cockpit/news",
        title: "News overview",
        description:
          "Compact news-feed cockpit view backed by recent news articles.",
      },
    ],
  },
  {
    heading: "Audit",
    items: [
      {
        href: "/cockpit/audit",
        title: "Audit hub",
        description:
          "Index of every cockpit audit tile (broker submit decisions, news-in-decision log, …).",
      },
    ],
  },
];

export default function CockpitHubPage() {
  const [modeState, setModeState] = useState<CockpitModeResponse | null>(null);
  const [autoPaperStatus, setAutoPaperStatus] = useState<AutoPaperStatusCard | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusLoading, setStatusLoading] = useState(true);
  const [updatingMode, setUpdatingMode] = useState<CockpitModeId | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const loadModeState = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await getCockpitMode();
      setModeState(response);
    } catch (fetchError) {
      setError(
        fetchError instanceof Error
          ? fetchError.message
          : "Failed to load cockpit mode state.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAutoPaperStatus = useCallback(async () => {
    setStatusLoading(true);
    setStatusError(null);
    try {
      const response = await getAutoPaperStatusCard();
      setAutoPaperStatus(response);
    } catch (fetchError) {
      setStatusError(
        fetchError instanceof Error
          ? fetchError.message
          : "Failed to load Auto Paper summary.",
      );
    } finally {
      setStatusLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadModeState();
    void loadAutoPaperStatus();
  }, [loadAutoPaperStatus, loadModeState]);

  const handleSelectMode = useCallback(async (modeId: CockpitModeId) => {
    setUpdatingMode(modeId);
    setError(null);
    setFeedback(null);
    try {
      const response = await updateCockpitMode(modeId);
      setModeState(response);
      const selected = response.modes.find((mode) => mode.id === response.current_mode);
      setFeedback(`${selected?.label ?? response.current_mode} is now the active cockpit mode.`);
    } catch (updateError) {
      setError(
        updateError instanceof Error
          ? updateError.message
          : "Failed to update cockpit mode.",
      );
    } finally {
      setUpdatingMode(null);
    }
  }, []);

  const currentMode = useMemo(
    () => modeState?.modes.find((mode) => mode.id === modeState.current_mode) ?? null,
    [modeState],
  );

  const selectableModes = useMemo(
    () => modeState?.modes.filter((mode) => mode.selectable) ?? [],
    [modeState],
  );

  const lockedModes = useMemo(
    () => modeState?.modes.filter((mode) => mode.locked) ?? [],
    [modeState],
  );

  return (
    <main className={styles.page}>
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>Cockpit</h1>
            <p className={styles.subtitle}>
              See the current operating mode, understand what remains blocked,
              and choose between Learning, Manual, and Auto Paper without
              unlocking live trading.
            </p>
          </div>
        </header>

        <div className={styles.driftLockNotice}>
          Drift lock: the selector below is advisory only. It does not replace
          backend trading guards, does not enable real-money routing, and does
          not unlock assisted live, live, or auto live.
        </div>

        {error && (
          <div className={styles.errorBanner} data-testid="cockpit-mode-error">
            {error}
          </div>
        )}

        {feedback && (
          <div className={styles.successBanner} data-testid="cockpit-mode-success">
            {feedback}
          </div>
        )}

        <section
          className={styles.modePanel}
          aria-label="Cockpit mode selector"
          data-testid="cockpit-mode-selector"
        >
          <div className={styles.modePanelHeader}>
            <div>
              <h2 className={styles.modePanelTitle}>Market Cockpit Mode Selector</h2>
              <p className={styles.modePanelSubtitle}>
                Risk first: mode selection changes operator intent only. The
                backend still decides what is allowed, and live trading remains
                blocked in this build.
              </p>
            </div>
            {currentMode && (
              <div
                className={styles.currentModeSummary}
                data-testid="cockpit-current-mode-summary"
              >
                <span className={styles.summaryLabel}>Current mode</span>
                <strong className={styles.summaryValue}>{currentMode.label}</strong>
                <span className={styles.summaryBody}>{currentMode.risk_note}</span>
              </div>
            )}
          </div>

          {loading && <div className={styles.loadingState}>Loading cockpit mode...</div>}

          {modeState && (
            <>
              <div className={styles.safetyStrip} data-testid="cockpit-safety-strip">
                <div className={styles.safetyItem}>
                  <span className={styles.safetyLabel}>Live trading</span>
                  <span className={styles.safetyValue}>
                    {modeState.live_trading_enabled ? "enabled" : "blocked"}
                  </span>
                </div>
                <div className={styles.safetyItem}>
                  <span className={styles.safetyLabel}>Auto live</span>
                  <span className={styles.safetyValue}>
                    {modeState.auto_live_enabled ? "enabled" : "blocked"}
                  </span>
                </div>
                <div className={styles.safetyItem}>
                  <span className={styles.safetyLabel}>Real money</span>
                  <span className={styles.safetyValue}>
                    {modeState.real_money_enabled ? "enabled" : "blocked"}
                  </span>
                </div>
                <div className={styles.safetyItem}>
                  <span className={styles.safetyLabel}>Paper submission</span>
                  <span className={styles.safetyValue}>
                    {modeState.global_safety_state.paper_order_submission_allowed
                      ? "allowed"
                      : "blocked"}
                  </span>
                </div>
              </div>

              <section className={styles.modeSection}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Selectable now</h3>
                  <p className={styles.sectionBody}>
                    These modes are available today. None of them can bypass
                    paper-boundary checks or turn on live trading.
                  </p>
                </div>

                <div className={styles.modeGrid}>
                  {selectableModes.map((mode) => {
                    const isActive = modeState.current_mode === mode.id;
                    const isPending = updatingMode === mode.id;
                    return (
                      <article
                        key={mode.id}
                        className={`${styles.modeCard} ${isActive ? styles.modeCardActive : ""}`}
                        data-testid={`cockpit-mode-card-${mode.id}`}
                      >
                        <div className={styles.modeCardHeader}>
                          <div>
                            <span className={styles.modeStatus}>{mode.status}</span>
                            <h4 className={styles.modeTitle}>{mode.label}</h4>
                          </div>
                          {isActive && <span className={styles.modePill}>active</span>}
                        </div>
                        <p className={styles.riskLead}>{mode.risk_note}</p>
                        <p className={styles.modeReason}>{mode.reason}</p>
                        <div className={styles.modeLists}>
                          <div>
                            <h5 className={styles.listTitle}>Can do</h5>
                            <ul className={styles.actionList}>
                              {mode.allowed_actions.map((action) => (
                                <li key={action}>{action}</li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h5 className={styles.listTitle}>Cannot do</h5>
                            <ul className={styles.actionList}>
                              {mode.blocked_actions.map((action) => (
                                <li key={action}>{action}</li>
                              ))}
                            </ul>
                          </div>
                        </div>
                        <div>
                          <h5 className={styles.listTitle}>Safety gates</h5>
                          <ul className={styles.actionList}>
                            {mode.safety_gates.map((gate) => (
                              <li key={gate}>{gate}</li>
                            ))}
                          </ul>
                        </div>
                        <button
                          type="button"
                          className={styles.modeButton}
                          onClick={() => void handleSelectMode(mode.id)}
                          disabled={isActive || Boolean(isPending)}
                          data-testid={`cockpit-select-${mode.id}`}
                        >
                          {isActive
                            ? "Currently selected"
                            : isPending
                              ? "Updating..."
                              : `Use ${mode.label}`}
                        </button>
                      </article>
                    );
                  })}
                </div>
              </section>

              <section className={styles.modeSection}>
                <div className={styles.sectionHeader}>
                  <h3 className={styles.sectionTitle}>Visible but locked</h3>
                  <p className={styles.sectionBody}>
                    These modes are shown so the product direction stays clear.
                    They remain disabled until explicit future safety phases are
                    completed and reviewed.
                  </p>
                </div>

                <div className={styles.modeGrid}>
                  {lockedModes.map((mode) => (
                    <article
                      key={mode.id}
                      className={`${styles.modeCard} ${styles.modeCardLocked}`}
                      data-testid={`cockpit-mode-card-${mode.id}`}
                    >
                      <div className={styles.modeCardHeader}>
                        <div>
                          <span className={styles.modeStatus}>locked</span>
                          <h4 className={styles.modeTitle}>{mode.label}</h4>
                        </div>
                        <span className={styles.modePill}>locked</span>
                      </div>
                      <p className={styles.riskLead}>{mode.risk_note}</p>
                      <p className={styles.modeReason}>{mode.reason}</p>
                      <div className={styles.modeLists}>
                        <div>
                          <h5 className={styles.listTitle}>Blocked</h5>
                          <ul className={styles.actionList}>
                            {mode.blocked_actions.map((action) => (
                              <li key={action}>{action}</li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <h5 className={styles.listTitle}>Safety gates</h5>
                          <ul className={styles.actionList}>
                            {mode.safety_gates.map((gate) => (
                              <li key={gate}>{gate}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                      <button
                        type="button"
                        className={`${styles.modeButton} ${styles.modeButtonLocked}`}
                        disabled
                        aria-disabled="true"
                        data-testid={`cockpit-select-${mode.id}`}
                      >
                        Locked in this build
                      </button>
                    </article>
                  ))}
                </div>
              </section>

              <section className={styles.notePanel}>
                <h3 className={styles.sectionTitle}>Backend safety notes</h3>
                <ul className={styles.actionList}>
                  {modeState.notes.map((note) => (
                    <li key={note}>{note}</li>
                  ))}
                  {modeState.global_safety_state.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </section>
            </>
          )}
        </section>

        <section className={styles.statusSummaryPanel} data-testid="cockpit-auto-paper-summary">
          <div className={styles.statusSummaryHeader}>
            <div>
              <h2 className={styles.modePanelTitle}>Auto Paper summary</h2>
              <p className={styles.modePanelSubtitle}>
                Concise read-only summary of Auto Paper posture, latest decision,
                and operator next action. Live trading remains locked.
              </p>
            </div>
            <Link href="/cockpit/auto-paper-status" className={styles.summaryLink}>
              Open full Auto Paper status
            </Link>
          </div>

          {statusError && <div className={styles.errorBanner}>{statusError}</div>}
          {statusLoading && <div className={styles.loadingState}>Loading Auto Paper summary...</div>}

          {autoPaperStatus && (
            <>
              <div className={styles.statusCallout}>
                <strong>{autoPaperStatus.headline}</strong>
                <span>{autoPaperStatus.subline}</span>
              </div>

              <div className={styles.statusSummaryGrid}>
                <div className={styles.statusSummaryItem}>
                  <span className={styles.summaryLabel}>Mode</span>
                  <strong className={styles.summaryValue}>{autoPaperStatus.mode}</strong>
                </div>
                <div className={styles.statusSummaryItem}>
                  <span className={styles.summaryLabel}>Last decision</span>
                  <strong className={styles.summaryValue}>{autoPaperStatus.last_decision}</strong>
                </div>
                <div className={styles.statusSummaryItem}>
                  <span className={styles.summaryLabel}>Open positions</span>
                  <strong className={styles.summaryValue}>
                    {autoPaperStatus.open_paper_positions_count} / {autoPaperStatus.max_open_paper_positions}
                  </strong>
                </div>
                <div className={styles.statusSummaryItem}>
                  <span className={styles.summaryLabel}>Live / Auto-live</span>
                  <strong className={styles.summaryValue}>
                    {autoPaperStatus.live_trading_locked && autoPaperStatus.auto_live_locked
                      ? "locked"
                      : "review"}
                  </strong>
                </div>
              </div>

              <p className={styles.statusNextAction}>
                <strong>Next action:</strong> {autoPaperStatus.operator_next_action}
              </p>

              <p className={styles.statusSafetyNote}>
                Simulation only. No real money orders can be placed from Auto Paper.
              </p>
            </>
          )}
        </section>

        {SECTIONS.map((section) => (
          <section key={section.heading} className={styles.section}>
            <h2 className={styles.sectionTitle}>{section.heading}</h2>
            <div className={styles.tileGrid}>
              {section.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={styles.tile}
                >
                  <div className={styles.tileHead}>
                    <h3 className={styles.tileTitle}>{item.title}</h3>
                    <span className={styles.tileBadge}>operator surface</span>
                  </div>
                  <p className={styles.tileDesc}>{item.description}</p>
                  <div className={styles.tileFoot}>
                    <span className={styles.linkPath}>{item.href}</span>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </main>
  );
}
