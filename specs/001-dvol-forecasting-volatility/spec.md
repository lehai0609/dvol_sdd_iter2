# Feature Specification: DVOL Forecasting & Volatility Trading (BTC primary, ETH optional)

**Feature Branch**: `001-dvol-forecasting-volatility`  
**Created**: 2025-09-15  
**Status**: Draft  
**Input**: User description: "Daily EOD forecasts of ΔDVOL for BTC (primary) and ETH (optional) over 1d/1w/2w horizons with outputs ({forecast_ΔDVOL, direction, confidence}); map to DVOL futures or delta-hedged options. Must achieve Sharpe ≥ 1.0 (net), Max DD ≤ 20%, hit-rate > 53%, tail-aware; daily EOD cadence, UTC cut-off 00:00; allowed data: DVOL OHLC, options summaries (volume, OI, net vega/proxy), spot/futures OHLCV + funding, on-chain daily summaries; strict anti-leakage; outputs include mapping doc, data contract, glossary, governance checklist; risks: regime shifts, overfitting, API/timezone issues, underestimated costs; guardrails: vega caps, event guardrails, daily stop-loss, kill-switch; out of scope: intraday, extra coins, discretionary overrides, infra, model architectures, microstructure details; open questions: options fields (net vega proxy), DVOL futures specs/liquidity & costs, absolute vs percentage ΔDVOL, on-chain inclusion lags."

## Execution Flow (main)
```
1. Parse user description from Input
	→ If empty: ERROR "No feature description provided"
2. Extract key concepts from description
	→ Identify: actors, actions, data, constraints
3. For each unclear aspect:
	→ Mark with [NEEDS CLARIFICATION: specific question]
4. Fill User Scenarios & Testing section
	→ If no clear user flow: ERROR "Cannot determine user scenarios"
5. Generate Functional Requirements
	→ Each requirement must be testable
	→ Mark ambiguous requirements
6. Identify Key Entities (if data involved)
7. Run Review Checklist
	→ If any [NEEDS CLARIFICATION]: WARN "Spec has uncertainties"
	→ If implementation details found: ERROR "Remove tech details"
8. Return: SUCCESS (spec ready for planning)
```

---

## ⚡ Quick Guidelines
- ✅ Focus on WHAT users need and WHY
- ❌ Avoid HOW to implement (no tech stack, APIs, code structure)
- 👥 Written for business stakeholders, not developers

### Section Requirements
- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (don't leave as "N/A")

### For AI Generation
When creating this spec from a user prompt:
1. **Mark all ambiguities**: Use [NEEDS CLARIFICATION: specific question] for any assumption you'd need to make
2. **Don't guess**: If the prompt doesn't specify something (e.g., "login system" without auth method), mark it
3. **Think like a tester**: Every vague requirement should fail the "testable and unambiguous" checklist item
4. **Common underspecified areas**:
	- User types and permissions
	- Data retention/deletion policies  
	- Performance targets and scale
	- Error handling behaviors
	- Integration requirements
	- Security/compliance needs

---

## User Scenarios & Testing *(mandatory)*

### Primary User Story
As a quant PM/researcher and trading ops user, I need reliable daily end-of-day forecasts of changes in 30-day implied volatility (DVOL) for BTC (primary) and optionally ETH over three horizons (t+1 day, t+7 days, t+14 days) with an accompanying, cost-aware stance mapping (long/short/flat) so the team can deploy disciplined, auditable volatility trades whose P&L primarily depends on IV changes.

### Acceptance Scenarios
1. Given the daily cut-off at 00:00 UTC and permitted inputs are available and frozen, When the forecasting process completes, Then for BTC a forecast object is produced for each horizon containing `forecast_ΔDVOL`, `direction` in {up, flat, down}, and `confidence`, and a conceptual stance mapping indicates whether to be long/short/flat based on horizon-specific decision thresholds that clear estimated costs.
2. Given ETH is marked as optional, When ETH input quality and governance gates pass, Then ETH forecast objects follow the same format and gating rules without impacting BTC deliverables.
3. Given a large volatility shock day, When forecasts and stance mapping are reviewed, Then tail-awareness is evident (e.g., thresholds/guards result in conservative stances) and governance artifacts record the decision context and data provenance.
4. Given out-of-sample backtest evaluation windows, When metrics are computed, Then results are traceable to the success criteria (Sharpe ≥ 1.0 net, max DD ≤ 20%, hit-rate > 53%) for approval and go/no-go decisions.

### Edge Cases
- Data outage or late arrival for any permitted domain (DVOL, options summary, funding, on-chain) on a given date.
- Timezone alignment issues (DST boundaries, exchange calendar quirks) that threaten cut-off discipline.
- Missing or redefined options summary fields (e.g., net vega proxy) causing feature drift.
- DVOL futures liquidity constraints near expiry or during off-peak hours affecting monetization viability.
- Extended calm or extreme regimes where thresholds require review to continue clearing costs.

## Requirements *(mandatory)*

### Functional Requirements
- **FR-001 (Core Output)**: Provide a daily end-of-day forecast for BTC ΔDVOL at three horizons (t+1d, t+7d, t+14d). ETH support is optional and gated by data quality and governance approval.
- **FR-002 (Forecast Object Schema)**: For each asset-date-horizon, produce `{ forecast_ΔDVOL, direction, confidence }`, where `direction ∈ {up, flat, down}` and `confidence` reflects uncertainty appropriate for decision-making (definition to be finalized in /plan).
- **FR-003 (Stance Mapping Artifact)**: Deliver a conceptual mapping document that translates forecast outputs into trade stances (long/short/flat) using horizon-specific decision thresholds designed to clear estimated costs; it must not prescribe algorithms or execution details.
- **FR-004 (Data Contract Artifact)**: Deliver a data contract that enumerates allowed input domains (DVOL daily OHLC; options summaries: volume, OI, net vega or defensible proxy; spot/futures OHLCV and aggregated funding; on-chain daily summaries), timestamp semantics, anti-leakage rules, and timezone normalization (UTC processing; convert only at reporting).
- **FR-005 (Cut-off Discipline)**: Enforce a fixed daily cut-off at 00:00 UTC; all features must be finalized and frozen prior to the target DVOL close; perform as-of joins; no leakage across the cut-off.
- **FR-006 (Scope Boundaries)**: Explicitly document IN-scope (BTC, optional ETH; DVOL futures and listed options for delta-hedged long-vol or risk-defined short-premium; daily EOD cadence; horizons 1d/1w/2w) and OUT-of-scope items (intraday/HFT; coins beyond ETH; discretionary overrides; production infra; model architectures/hyperparameters; execution microstructure).
- **FR-007 (Governance Artifacts)**: Provide a glossary for non-quant stakeholders (e.g., DVOL, IV, net vega, delta-hedged straddle, funding rate, vega exposure), an approval checklist covering data quality, spec–code traceability, and high-level audit logging expectations, and maintain change-control notes.
- **FR-008 (Success Criteria Traceability)**: Define how each success criterion is measured and traced in evaluation (Sharpe ≥ 1.0 net; max DD ≤ 20%; directional hit-rate > 53%; tail-day behavior), without prescribing modeling methods.
- **FR-009 (Risk Guardrails Expectations)**: State implementation-level risk controls to be respected (hard caps on vega exposure per asset; event guardrails for jump/funding spikes; daily stop-loss; kill-switch) as constraints, deferring design specifics to /plan.
- **FR-010 (Reproducibility & Auditability)**: Runs must be reproducible and auditable, with spec–code traceability and run metadata sufficient for governance review (exact mechanisms deferred to /plan).
- **FR-011 (Optional External Data Gate)**: External attention data (e.g., Google Trends) MAY be introduced only if strictly timestamped pre–cut-off and approved; otherwise it remains out of scope.
- **FR-012 (Tail Awareness Reporting)**: Provide visibility into tail/shock days and how stance mapping behaves under such conditions, at the "what" level (no algorithmic prescriptions).
- **FR-013 (Quality Gates)**: Include tests/controls that detect time-zone mishandling, options field redefinitions, and input outages; failures should block forecasts pending governance triage (mechanics deferred to /plan).
- **FR-014 (Open Questions Resolution – Finalized)**:
	- **FR-014.a — Options “net vega” availability/definition**
		- Primary source: `GET /v1/data/summary/deribit/options/greeks/maturities/` (params: `underlying=BTC|ETH`, `enddate`, `limit`, `return`) using fields `net_vega`, `avg_iv`, `usd_volume`, etc.
		- Feature spec: Use daily NetVega (level) and a 5-day z-score; maintain `options_availability_flag` when the endpoint returns < 70% of typical volume days.
		- Fallbacks: If the endpoint fails for a day, compute trade-flow net vega from trade prints; if not possible, approximate inventory-change vega via ΔOI × prior-day vega.
	- **FR-014.b — DVOL futures specs/liquidity + costs**
		- Data coverage: Use CDD DVOL index OHLC to validate target behavior (`/v1/data/ohlc/deribit/volatility?symbol=BTC|ETH`). Use CDD futures OHLC for the symbols we trade if available (`/v1/data/ohlc/deribit/futures/?symbol=...`).
		- Contract specs: Not present in CDD; source contract size, tick, and settlement from Deribit product docs and keep in a static config checked into the repo.
		- Liquidity gates: Require 20-day median USD notional volume above a threshold (e.g., $2m) for the traded symbol before enabling the strategy; if the required symbol isn’t covered or volume is insufficient, fall back to the options expression.
		- Cost model (conservative backtest): fees = taker 5 bps / maker −1 bps (tunable by account tier); slippage = ½ inside-spread for small clips, 1× spread for larger; spread estimates come from recorded quotes where available, else a minimum of 0.1 tick. Spread/book data aren’t in CDD and will be logged from the execution venue.
	- **FR-014.c — Target: absolute vs. percentage ΔDVOL**
		- Decision: t+1d target = absolute ΔDVOL (points); t+7d/t+14d auxiliary targets = percentage (or log) ΔDVOL.
		- Training/reporting: Train on standardized targets (z-score within the rolling train window) but gate trades on point forecasts, since DVOL futures P&L is linear in points.
	- **FR-014.d — On-chain inclusion criteria and lags**
		- Source: `GET /v1/data/summary/blockchain/blocks/?symbol=btc|eth` provides daily tx/blocks/gas/etc.
		- Policy: Enforce t−1 lag for all on-chain inputs unless later verified as same-day available before 00:00 UTC; allow 1-day forward-fill with an `onchain_is_imputed` flag; drop a day if > 30% of on-chain features are missing/imputed.

### Key Entities *(include if feature involves data)*
- **Forecast Object**: The unit of decision per asset-date-horizon with fields `forecast_ΔDVOL` (numeric; absolute or percentage pending clarification), `direction` (up/flat/down), and `confidence` (scale/definition to be finalized). Used by the stance mapping.
- **Data Contract**: Canonical description of permitted inputs, timestamp rules (UTC), cut-off discipline (00:00 UTC), as-of join keys, anti-leakage expectations, inclusion/exclusion gates for optional data, and data quality flags such as `options_availability_flag` and `onchain_is_imputed` plus drop policies (e.g., > 30% on-chain missing/imputed → drop day).
- **Stance Mapping (Conceptual)**: Policy document that translates forecast signals into long/short/flat trade stances using horizon-specific thresholds that clear estimated costs; does not specify execution or sizing algorithms.
- **Governance & Glossary**: A non-technical glossary of core terms and an approval checklist outlining data quality gates, traceability expectations, and audit-logging at a high level; also records scope boundaries and change history.
- **Success Metrics Catalog**: Definition of evaluation metrics tied to approval gates (Sharpe, max DD, hit-rate, tail-day behavior) to ensure traceable sign-off.

---

## Review & Acceptance Checklist
*GATE: Automated checks run during main() execution*

### Content Quality
- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

### Requirement Completeness
- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous  
- [ ] Success criteria are measurable
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

---

## Execution Status
*Updated by main() during processing*

- [x] User description parsed
- [x] Key concepts extracted
- [x] Ambiguities marked
- [x] User scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Review checklist passed

---

