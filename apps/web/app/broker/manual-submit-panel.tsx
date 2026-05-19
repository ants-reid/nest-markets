"use client";

import type { Dispatch, SetStateAction } from "react";
import type {
  BrokerOrderDryRunIssue,
  BrokerOrderDryRunResult,
  DryRunPreflightContext,
  RiskLimitSnapshot,
} from "../../lib/api/broker";
import styles from "../../styles/pages/broker.module.css";

export type SubmitFormState = {
  ticker: string;
  side: "BUY" | "SELL";
  quantity: string;
  orderType: "MARKET" | "LIMIT";
  limitPrice: string;
};

export type SubmitFormErrors = {
  ticker?: string;
  quantity?: string;
  limitPrice?: string;
};

function PreflightContextPanel({ dryRun }: { dryRun: BrokerOrderDryRunResult }) {
  const ctx: DryRunPreflightContext | null = dryRun.preflight_context ?? null;
  const warnings: BrokerOrderDryRunIssue[] = dryRun.warnings ?? [];
  const snap: RiskLimitSnapshot | null = ctx?.risk_limit_snapshot ?? null;

  if (!ctx && warnings.length === 0) return null;

  function fmtVal(val: number | null | undefined, prefix: string = "$"): string {
    if (val == null) return "—";
    return `${prefix}${val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  }

  function fmtInt(val: number | null | undefined): string {
    if (val == null) return "—";
    return val.toLocaleString("en-US");
  }

  return (
    <div className={styles.preflightPanel} data-testid="broker-preflight-context-panel">
      <div className={styles.preflightHeader}>
        <span className={styles.preflightTitle}>Preflight Context</span>
        <span className={styles.preflightAdvisoryBadge}>Advisory Only</span>
      </div>
      <p className={styles.preflightDisclaimer}>
        Preflight context is advisory only. Context is based on the currently active broker account. Broker submit behaviour is unchanged. Risk and halt checks are not yet enforced on submit.
      </p>

      {ctx && (
        <div className={styles.preflightGrid}>
          {dryRun.estimated_notional != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-estimated-notional">
              <span className={styles.preflightLabel}>Est. Notional</span>
              <span className={styles.preflightValue}>{fmtVal(dryRun.estimated_notional)}</span>
            </div>
          )}
          {ctx.cash_balance != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-cash-balance">
              <span className={styles.preflightLabel}>Cash Balance</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.cash_balance)}</span>
            </div>
          )}
          {ctx.buying_power != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-buying-power">
              <span className={styles.preflightLabel}>Buying Power</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.buying_power)}</span>
            </div>
          )}
          {ctx.open_position_count != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-open-positions">
              <span className={styles.preflightLabel}>Open Positions</span>
              <span className={styles.preflightValue}>{fmtInt(ctx.open_position_count)}</span>
            </div>
          )}
          {ctx.current_symbol_exposure != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-symbol-exposure">
              <span className={styles.preflightLabel}>Symbol Exposure</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.current_symbol_exposure)}</span>
            </div>
          )}
          {ctx.estimated_post_trade_symbol_exposure != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-post-trade-symbol-exposure">
              <span className={styles.preflightLabel}>Post-Trade Symbol Exp.</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.estimated_post_trade_symbol_exposure)}</span>
            </div>
          )}
          {ctx.current_total_exposure != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-total-exposure">
              <span className={styles.preflightLabel}>Total Exposure</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.current_total_exposure)}</span>
            </div>
          )}
          {ctx.estimated_post_trade_total_exposure != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-post-trade-total-exposure">
              <span className={styles.preflightLabel}>Post-Trade Total Exp.</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.estimated_post_trade_total_exposure)}</span>
            </div>
          )}
          {ctx.daily_pnl != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-daily-pnl">
              <span className={styles.preflightLabel}>Daily P&amp;L</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.daily_pnl)}</span>
            </div>
          )}
          {ctx.daily_loss != null && (
            <div className={styles.preflightItem} data-testid="broker-preflight-daily-loss">
              <span className={styles.preflightLabel}>Daily Loss</span>
              <span className={styles.preflightValue}>{fmtVal(ctx.daily_loss)}</span>
            </div>
          )}
        </div>
      )}

      {snap && (
        <div className={styles.preflightSnapshot} data-testid="broker-preflight-risk-snapshot">
          <span className={styles.preflightSnapshotTitle}>Risk Limit Snapshot</span>
          <div className={styles.preflightGrid}>
            {snap.max_order_notional != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Max Order Notional</span>
                <span className={styles.preflightValue}>{fmtVal(snap.max_order_notional)}</span>
              </div>
            )}
            {snap.max_total_exposure != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Max Total Exposure</span>
                <span className={styles.preflightValue}>{fmtVal(snap.max_total_exposure)}</span>
              </div>
            )}
            {snap.max_symbol_exposure != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Max Symbol Exposure</span>
                <span className={styles.preflightValue}>{fmtVal(snap.max_symbol_exposure)}</span>
              </div>
            )}
            {snap.daily_loss_limit_amount != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Daily Loss Limit</span>
                <span className={styles.preflightValue}>{fmtVal(snap.daily_loss_limit_amount)}</span>
              </div>
            )}
            {snap.daily_loss_limit_pct != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Daily Loss Limit %</span>
                <span className={styles.preflightValue}>{snap.daily_loss_limit_pct}%</span>
              </div>
            )}
            {snap.max_open_positions != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Max Open Positions</span>
                <span className={styles.preflightValue}>{snap.max_open_positions}</span>
              </div>
            )}
            {snap.max_trades_per_day != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Max Trades/Day</span>
                <span className={styles.preflightValue}>{snap.max_trades_per_day}</span>
              </div>
            )}
            {snap.min_cash_buffer != null && (
              <div className={styles.preflightItem}>
                <span className={styles.preflightLabel}>Min Cash Buffer</span>
                <span className={styles.preflightValue}>{fmtVal(snap.min_cash_buffer)}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {warnings.length > 0 && (
        <div className={styles.preflightWarnings} data-testid="broker-preflight-warnings">
          <span className={styles.preflightWarningsTitle}>Advisory Warnings</span>
          <ul className={styles.preflightWarningsList}>
            {warnings.map((w, i) => (
              <li key={i} className={styles.preflightWarningItem} data-testid="broker-preflight-warning-item">
                <span className={styles.preflightWarningCode}>{w.code}</span>
                <span className={styles.preflightWarningMsg}>{w.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function BrokerManualSubmitPanel({
  form,
  setForm,
  formErrors,
  setFormErrors,
  dryRun,
  setDryRun,
  dryRunError,
  submitMessage,
  submitError,
  runningDryRun,
  runningSubmit,
  confirmPending,
  setConfirmPending,
  runDryRun,
  handleSubmitClick,
  runSubmit,
  formatMoney,
}: {
  form: SubmitFormState;
  setForm: Dispatch<SetStateAction<SubmitFormState>>;
  formErrors: SubmitFormErrors;
  setFormErrors: Dispatch<SetStateAction<SubmitFormErrors>>;
  dryRun: BrokerOrderDryRunResult | null;
  setDryRun: Dispatch<SetStateAction<BrokerOrderDryRunResult | null>>;
  dryRunError: string | null;
  submitMessage: string | null;
  submitError: string | null;
  runningDryRun: boolean;
  runningSubmit: boolean;
  confirmPending: boolean;
  setConfirmPending: Dispatch<SetStateAction<boolean>>;
  runDryRun: () => Promise<void>;
  handleSubmitClick: () => void;
  runSubmit: () => Promise<void>;
  formatMoney: (value: number, currency?: string) => string;
}) {
  return (
    <section className={styles.submitPanel} data-testid="broker-manual-submit-panel">
      <div className={styles.submitHeaderRow}>
        <h2 className={styles.sectionTitle}>Manual Paper Order Submit</h2>
        <span className={styles.submitHint}>Dry run is required before submit</span>
      </div>

      <div className={styles.submitGrid}>
        <label className={styles.submitField}>
          <span>Symbol</span>
          <input
            data-testid="broker-submit-ticker"
            value={form.ticker}
            className={formErrors.ticker ? styles.submitFieldInputError : undefined}
            onChange={(e) => {
              setForm((state) => ({ ...state, ticker: e.target.value }));
              setDryRun(null);
              setConfirmPending(false);
              setFormErrors((state) => ({ ...state, ticker: undefined }));
            }}
          />
          {formErrors.ticker && (
            <span className={styles.submitFieldError} data-testid="broker-submit-ticker-error">
              {formErrors.ticker}
            </span>
          )}
        </label>
        <label className={styles.submitField}>
          <span>Side</span>
          <select
            data-testid="broker-submit-side"
            value={form.side}
            onChange={(e) => {
              setForm((state) => ({ ...state, side: e.target.value as "BUY" | "SELL" }));
              setDryRun(null);
              setConfirmPending(false);
            }}
          >
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>
        </label>
        <label className={styles.submitField}>
          <span>Quantity</span>
          <input
            data-testid="broker-submit-quantity"
            type="number"
            min="0"
            step="1"
            value={form.quantity}
            className={formErrors.quantity ? styles.submitFieldInputError : undefined}
            onChange={(e) => {
              setForm((state) => ({ ...state, quantity: e.target.value }));
              setDryRun(null);
              setConfirmPending(false);
              setFormErrors((state) => ({ ...state, quantity: undefined }));
            }}
          />
          {formErrors.quantity && (
            <span className={styles.submitFieldError} data-testid="broker-submit-quantity-error">
              {formErrors.quantity}
            </span>
          )}
        </label>
        <label className={styles.submitField}>
          <span>Order Type</span>
          <select
            data-testid="broker-submit-order-type"
            value={form.orderType}
            onChange={(e) => {
              setForm((state) => ({ ...state, orderType: e.target.value as "MARKET" | "LIMIT" }));
              setDryRun(null);
              setConfirmPending(false);
              setFormErrors((state) => ({ ...state, limitPrice: undefined }));
            }}
          >
            <option value="MARKET">MARKET</option>
            <option value="LIMIT">LIMIT</option>
          </select>
        </label>
        {form.orderType === "LIMIT" && (
          <label className={styles.submitField}>
            <span>Limit Price</span>
            <input
              data-testid="broker-submit-limit-price"
              type="number"
              min="0"
              step="0.01"
              value={form.limitPrice}
              className={formErrors.limitPrice ? styles.submitFieldInputError : undefined}
              onChange={(e) => {
                setForm((state) => ({ ...state, limitPrice: e.target.value }));
                setDryRun(null);
                setConfirmPending(false);
                setFormErrors((state) => ({ ...state, limitPrice: undefined }));
              }}
            />
            {formErrors.limitPrice && (
              <span className={styles.submitFieldError} data-testid="broker-submit-limit-price-error">
                {formErrors.limitPrice}
              </span>
            )}
          </label>
        )}
      </div>

      {!confirmPending && (
        <div className={styles.submitActions}>
          <button
            type="button"
            data-testid="broker-submit-dry-run"
            className={styles.refreshButton}
            onClick={() => void runDryRun()}
            disabled={runningDryRun || runningSubmit}
          >
            {runningDryRun ? "Running Dry Run..." : "Run Dry Run"}
          </button>
          <button
            type="button"
            data-testid="broker-submit-order"
            className={dryRun?.status === "ready" ? styles.submitBtnReady : styles.submitBtnBlocked}
            onClick={handleSubmitClick}
            disabled={runningDryRun || runningSubmit}
          >
            Submit Paper Order
          </button>
        </div>
      )}

      {confirmPending && dryRun?.status === "ready" && (
        <div className={styles.submitConfirmPanel} data-testid="broker-submit-confirm-panel">
          <span className={styles.submitConfirmText}>
            Confirm paper order: {form.side} {form.quantity} {form.ticker.trim().toUpperCase()}
            {form.orderType === "LIMIT" && form.limitPrice ? ` @ LIMIT $${form.limitPrice}` : " @ MARKET"}
          </span>
          <div className={styles.submitConfirmActions}>
            <button
              type="button"
              data-testid="broker-submit-confirm"
              className={styles.confirmBtn}
              onClick={() => void runSubmit()}
              disabled={runningSubmit}
            >
              {runningSubmit ? "Submitting..." : "Confirm"}
            </button>
            <button
              type="button"
              data-testid="broker-submit-cancel"
              className={styles.cancelBtn}
              onClick={() => setConfirmPending(false)}
              disabled={runningSubmit}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {dryRun && (
        <div
          className={dryRun.status === "ready" ? styles.dryRunResultReady : styles.dryRunResultInvalid}
          data-testid="broker-submit-dry-run-result"
        >
          {dryRun.status === "ready" ? "✓" : "✗"} Dry Run: {dryRun.status.toUpperCase()}
          {dryRun.estimated_notional !== null ? ` · Est. notional ${formatMoney(dryRun.estimated_notional)}` : ""}
          {dryRun.issues.length > 0 && (
            <ul className={styles.dryRunIssues} data-testid="broker-submit-dry-run-issues">
              {dryRun.issues.map((issue, index) => (
                <li key={index} className={styles.dryRunIssueItem}>
                  {issue.message ?? issue.code ?? "Unknown issue"}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {dryRun && <PreflightContextPanel dryRun={dryRun} />}
      {dryRun && (
        <p className={styles.dryRunAdvisoryNote} data-testid="broker-dry-run-advisory-note">
          Advisory only. Context is based on the currently active broker account.
        </p>
      )}
      {dryRunError && (
        <div className={styles.submitError} data-testid="broker-submit-dry-run-error">
          {dryRunError}
        </div>
      )}
      {submitMessage && (
        <div className={styles.submitSuccess} data-testid="broker-submit-success">
          {submitMessage}
        </div>
      )}
      {submitError && (
        <div className={styles.submitError} data-testid="broker-submit-error">
          {submitError}
        </div>
      )}
    </section>
  );
}