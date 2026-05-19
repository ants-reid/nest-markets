# Implementation Tickets: Market Hunter MVP Refactor

**Scope:** First 30 tickets (Phase 1-2, ~2 weeks)  
**Format:** Each ticket includes: title, description, acceptance criteria, dependencies, testing requirements, and effort estimate

---

## Parked: Dual Broker Account Visibility

**Status:** Not scheduled — parked after MH-42 scope discussion.

**Description:**
Show paper and live account panels side-by-side so the operator can compare account
readiness without switching modes. No execution changes.

**What it would require:**
- Two separate IBKR Client Portal Gateway instances (paper accounts use `DU*` IDs; live
  use `U*` IDs; IBKR does not allow mixing them in a single gateway session)
- Backend changes: hold two `IBKRAdapter` connections; expose `GET /broker/account?mode=paper`
  and `GET /broker/account?mode=live`
- Frontend changes: dual-panel layout with independent polling loops for each mode
- No order submission changes; live execution gate remains unchanged

**Prerequisite:** Live IBKR gateway credentials and a live account ID (`U*`) must be
configured before this is meaningful.

**Suggested ticket ID:** MH-future-dual-broker-panels

---

## PHASE 1: FRONTEND SHELL MODERNIZATION (Tickets 1-15)

### Ticket 1: Create AppShell Component

**Title:** Implement `components/shell/AppShell.tsx` — Top-level layout wrapper

**Description:**
AppShell is the root layout container for all authenticated pages. It combines Sidebar, Topbar, and content area with responsive behavior.

**Files to create:**
- `apps/web/components/shell/AppShell.tsx`
- `apps/web/components/shell/AppShell.module.css`

**Acceptance Criteria:**
1. AppShell renders sidebar + topbar + children
2. Sidebar is sticky on left (desktop), collapsible on mobile
3. Topbar is fixed on top, contains branding + user menu
4. Content area has responsive padding/margin
5. Dark/light theme support via CSS variables
6. No inline `style={{}}` objects; all styles in CSS module

**Dependencies:**
- Sidebar component (Ticket 2)
- Topbar component (Ticket 3)

**Testing:**
- Renders at 390px, 768px, 1024px, 1440px
- Theme toggle works (localStorage persists)
- Sidebar collapse/expand works on mobile
- Visual snapshots (light + dark mode)

**Effort:** 4 points

---

### Ticket 2: Create Sidebar Component

**Title:** Implement `components/shell/Sidebar.tsx` — Navigation sidebar with sections

**Description:**
Sidebar contains app navigation links grouped by section (core, analytics, admin). Responsive: full-width on mobile, fixed-width on desktop, collapses on tablet.

**Files to create:**
- `apps/web/components/shell/Sidebar.tsx`
- `apps/web/components/shell/Sidebar.module.css`
- `apps/web/components/shell/SidebarSection.tsx`

**Acceptance Criteria:**
1. Sidebar sections: Core (Home, Dashboard, Execution), Analytics (Analytics, Performance), Admin (Approvals, Alerts)
2. Active link styling via `usePathname()`
3. Collapse/expand toggle on mobile
4. Sticky positioning on desktop
5. Logo/branding at top
6. All links use Next.js Link component

**Dependencies:**
- PageHeader component (Ticket 4) for consistency
- Current route data (usePathname hook)

**Testing:**
- Active link highlighting works
- Collapse toggles on mobile
- All 10 routes navigable from sidebar
- Visual snapshots (collapsed + expanded)
- No broken links

**Effort:** 5 points

---

### Ticket 3: Create Topbar Component

**Title:** Implement `components/shell/Topbar.tsx` — Fixed header with user menu

**Description:**
Topbar shows branding, search hint, theme toggle, and user menu. Fixed on top, spans full width. Contains MH logo, Learn button, theme toggle, user dropdown.

**Files to create:**
- `apps/web/components/shell/Topbar.tsx`
- `apps/web/components/shell/Topbar.module.css`

**Acceptance Criteria:**
1. MH logo/wordmark on left
2. Learn button (toggles LearningModePanel)
3. Theme toggle (Dark/Light)
4. User menu (name, logout, settings) — scaffold OK
5. Responsive: logo shrinks on mobile
6. Fixed positioning, z-index above sidebar

**Dependencies:**
- LearningModePanel (already exists, just import)

**Testing:**
- Learn button opens panel
- Theme toggle switches and persists
- User menu opens/closes
- Visual snapshots (responsive breakpoints)
- Theme persistence across navigation

**Effort:** 4 points

---

### Ticket 4: Create PageHeader Component

**Title:** Implement `components/shell/PageHeader.tsx` — Consistent page title + breadcrumb area

**Description:**
PageHeader wraps the title, subtitle, and optional breadcrumbs/actions at the top of each page content area. Used by dashboard, analytics, execution, etc.

**Files to create:**
- `apps/web/components/shell/PageHeader.tsx`
- `apps/web/components/shell/PageHeader.module.css`

**Acceptance Criteria:**
1. Props: title (string), subtitle (optional), breadcrumbs (optional), actions (optional ReactNode)
2. Title is bold, 24-28px
3. Subtitle is muted, 13-14px
4. Breadcrumbs are dot-separated links
5. Actions (buttons, filters) on right side, flex wrap on mobile
6. Background: light surface color with border bottom

**Dependencies:**
- None (reusable primitive)

**Testing:**
- Renders with all prop combinations
- Breadcrumbs navigation works
- Actions align right on desktop, wrap on mobile
- Typography scales at responsive breakpoints

**Effort:** 3 points

---

### Ticket 5: Create Card UI Component

**Title:** Implement `components/ui/Card.tsx` — Basic container primitive

**Description:**
Card is the foundational container for grouped content. Handles border, background, shadow, padding, hover states.

**Files to create:**
- `apps/web/components/ui/Card.tsx`
- `apps/web/components/ui/Card.module.css`

**Acceptance Criteria:**
1. Props: children, className (optional), interactive (boolean, adds hover state)
2. Padding: 16-20px
3. Border: 1px solid --surface-border
4. Background: --surface-fill
5. Shadow: --surface-shadow
6. Hover (if interactive): subtle bg change, cursor pointer
7. Border radius: 12-16px

**Dependencies:**
- CSS variables (already in globals.css)

**Testing:**
- Renders with/without interactive prop
- Hover state visual snapshot
- Dark/light theme rendering
- Padding/spacing correct

**Effort:** 2 points

---

### Ticket 6: Create MetricCard Component

**Title:** Implement `components/ui/MetricCard.tsx` — Metric display card (replaces StatCard)

**Description:**
MetricCard displays a single metric: title, large value, optional description, optional link. Replaces current StatCard.tsx with modern styling and consistent layout.

**Files to create:**
- `apps/web/components/ui/MetricCard.tsx`
- `apps/web/components/ui/MetricCard.module.css`

**Acceptance Criteria:**
1. Props: title (string), value (string), description (string), href (optional), trend (optional: "up" | "down" | "neutral")
2. Min height: 150px
3. Value: 32-36px, bold, using --accent-highlight
4. Trend indicator: small badge with color coding
5. Optional href wraps in Link
6. Responsive: full-width on mobile, 1-2 per row on tablet, 3-4 per row on desktop

**Dependencies:**
- Card component (Ticket 5)
- Badge component (Ticket 8)

**Testing:**
- Renders with/without trend and href
- Trend badge colors correct (up=green, down=red, neutral=gray)
- Click navigates if href provided
- Visual snapshots (all combinations)

**Effort:** 3 points

---

### Ticket 7: Create Panel Component

**Title:** Implement `components/ui/Panel.tsx` — Larger content container with header

**Description:**
Panel is a Card variant with optional title, subtitle, controls, and legend slots. Used for chart sections, data tables, detail views.

**Files to create:**
- `apps/web/components/ui/Panel.tsx`
- `apps/web/components/ui/Panel.module.css`

**Acceptance Criteria:**
1. Props: title (ReactNode), subtitle (optional), controls (optional), legend (optional), children, contentGap (number, default 12)
2. Header: flex row with title section + controls on right
3. Optional legend below header
4. Content: children with configurable gap
5. All styling via CSS module, no inline styles
6. Inherits Card styling (border, shadow, bg)

**Dependencies:**
- Card component (Ticket 5)

**Testing:**
- Renders with all slot combinations
- Controls and legend alignment correct
- Content gap adjusts spacing
- Visual snapshots (full variations)

**Effort:** 3 points

---

### Ticket 8: Create Button Component

**Title:** Implement `components/ui/Button.tsx` — Semantic button primitive

**Description:**
Button is a styled `<button>` or Link wrapper supporting variants (primary, secondary, ghost), sizes (sm, md, lg), states (disabled, loading).

**Files to create:**
- `apps/web/components/ui/Button.tsx`
- `apps/web/components/ui/Button.module.css`

**Acceptance Criteria:**
1. Props: variant ("primary" | "secondary" | "ghost"), size ("sm" | "md" | "lg"), disabled, loading, icon (optional), asLink (optional href)
2. Primary: --accent-primary bg, white text, hover darker
3. Secondary: --surface-soft bg, --text-strong text, hover border
4. Ghost: transparent, text only, border on hover
5. Sizes: sm=28px, md=36px, lg=44px (min height for touch)
6. Loading state: spinner icon
7. Icon support: leading icon optional

**Dependencies:**
- None (uses CSS variables)

**Testing:**
- All variant/size combinations render
- Disabled state prevents click
- Loading state shows spinner
- asLink renders as Link component
- Touch targets >=44px on mobile
- Visual snapshots (all states)

**Effort:** 4 points

---

### Ticket 9: Create Badge Component

**Title:** Implement `components/ui/Badge.tsx` — Status/label badge

**Description:**
Badge displays a small, colored label for status, tags, or categories. Variants: default, success, warning, danger, info.

**Files to create:**
- `apps/web/components/ui/Badge.tsx`
- `apps/web/components/ui/Badge.module.css`

**Acceptance Criteria:**
1. Props: variant ("default" | "success" | "warning" | "danger" | "info"), children (string)
2. Padding: 4-8px horizontal, 2-4px vertical
3. Font size: 12px, uppercase
4. Color mapping: success=--state-success, warning=--state-warning, danger=--state-danger, info=--state-info
5. Border radius: 4-6px (pill shape)
6. Optional icon (leading)

**Dependencies:**
- None

**Testing:**
- All variant colors render correctly
- Text centering and truncation correct
- Dark/light theme rendering
- Visual snapshots (all variants)

**Effort:** 2 points

---

### Ticket 10: Refactor Nav.tsx into Shell System

**Title:** Replace `components/Nav.tsx` with `components/shell/` exports

**Description:**
Nav.tsx currently exists as a monolithic component. Replace its contents by:
1. Extracting sidebar nav items into Sidebar.tsx
2. Extracting theme toggle + Learn button into Topbar.tsx
3. Remove Nav.tsx
4. Update (shell)/layout.tsx to use AppShell

**Files to delete:**
- `apps/web/components/Nav.tsx`

**Files to update:**
- `apps/web/app/(shell)/layout.tsx` — import AppShell instead of Nav

**Acceptance Criteria:**
1. All 10 navigation links present in Sidebar
2. Learn button in Topbar
3. Theme toggle in Topbar
4. (shell)/layout.tsx renders AppShell with children
5. No visual diff vs current Nav (except improved spacing/layout)
6. All Playwright tests still pass

**Dependencies:**
- Tickets 2, 3, 4 (Sidebar, Topbar, PageHeader)

**Testing:**
- All routes navigable
- Active link highlighting works
- Theme toggle persists
- Learn button opens panel
- Visual regression snapshots
- All 20 smoke tests pass

**Effort:** 3 points

---

### Ticket 11: Refactor StatCard.tsx to MetricCard

**Title:** Replace `components/StatCard.tsx` with `components/ui/MetricCard.tsx`

**Description:**
StatCard is the current reusable metric display. Replace with new MetricCard that:
1. Uses Card primitive
2. Supports trend indicators
3. Cleaner styling
4. CSS module-based

**Files to delete:**
- `apps/web/components/StatCard.tsx`

**Files to update:**
- `apps/web/components/PersonalDashboard.tsx` — import MetricCard instead of StatCard
- All other pages using StatCard

**Acceptance Criteria:**
1. Same visual appearance as current StatCard
2. No prop changes needed (metric cards still work the same)
3. All PersonalDashboard metrics render
4. MetricCard supports new trend prop (optional, backward compat)
5. Visual regression: no diff vs current

**Dependencies:**
- Ticket 6 (MetricCard)
- Ticket 5 (Card)

**Testing:**
- All metrics in PersonalDashboard render
- Trend indicators work
- Trend colors correct (up=green, down=red)
- Visual snapshots (metrics grid)
- Responsive layout correct

**Effort:** 2 points

---

### Ticket 12: Upgrade ChartPanel Component

**Title:** Refactor `components/chart/ChartPanel.tsx` to use Panel primitive

**Description:**
ChartPanel currently has inline styling. Refactor to:
1. Use Panel component
2. Move styles to CSS module
3. Keep all existing props/behavior
4. Add support for contentGap prop

**Files to update:**
- `apps/web/components/chart/ChartPanel.tsx`
- Create `apps/web/components/chart/ChartPanel.module.css`

**Acceptance Criteria:**
1. Uses Panel component internally
2. All props work as before (title, subtitle, controls, legend, children, contentGap)
3. No visual regression vs current
4. CSS-module based, no inline `style={}`
5. Responsive gap adjustments work

**Dependencies:**
- Ticket 7 (Panel)

**Testing:**
- ChartPanel renders with all prop combos
- Legend, controls, subtitle display correctly
- Content gap adjusts spacing
- Visual snapshots (analytics page charts)

**Effort:** 2 points

---

### Ticket 13: Split PersonalDashboard into Sections

**Title:** Refactor `components/PersonalDashboard.tsx` into section components

**Description:**
PersonalDashboard is a monolithic 400+ line component. Split into:
1. DashboardMetricsSection
2. DashboardChartsSection
3. DashboardAlertsSection
Keep all data loading/state in parent, pass props down.

**Files to create:**
- `apps/web/components/dashboard/DashboardMetricsSection.tsx`
- `apps/web/components/dashboard/DashboardChartsSection.tsx`
- `apps/web/components/dashboard/DashboardAlertsSection.tsx`

**Files to update:**
- `apps/web/components/PersonalDashboard.tsx` — refactored to orchestrate sections

**Acceptance Criteria:**
1. PersonalDashboard still loads all data, passes to sections
2. Each section is <100 lines, focused render logic
3. All metrics, charts, alerts render correctly
4. No visual or functional diff
5. Easier to test and modify in future

**Dependencies:**
- Tickets 5, 6, 7 (Card, MetricCard, Panel primitives)

**Testing:**
- Dashboard page renders without errors
- All sections visible
- Metrics grid, charts, alerts display
- Responsive layout works
- Visual snapshots (full dashboard)

**Effort:** 4 points

---

### Ticket 14: Move Styles to CSS Modules

**Title:** Eliminate inline `style={{}}` objects in pages and components

**Description:**
Dashboard, Analytics, Execution pages use inline `style={{}}` for layout. Move all to CSS modules:
1. Create `styles/pages/analytics.module.css`
2. Create `styles/pages/execution.module.css`
3. Create `styles/pages/dashboard.module.css`
4. Update components to use className from modules

**Files to create:**
- `apps/web/styles/pages/dashboard.module.css`
- `apps/web/styles/pages/analytics.module.css`
- `apps/web/styles/pages/execution.module.css`

**Files to update:**
- `apps/web/app/dashboard/page.tsx`
- `apps/web/app/analytics/page.tsx`
- `apps/web/app/execution/page.tsx`

**Acceptance Criteria:**
1. Zero inline `style={{}}` in page/component files
2. All layout/spacing from CSS modules
3. CSS variable references preserved
4. No visual changes vs current
5. Responsive rules in CSS, not inline

**Dependencies:**
- Tickets 1-13 (all components should already use CSS modules)

**Testing:**
- All 3 pages render correctly
- Layout matches before refactor
- Responsive breakpoints work
- Visual snapshots (desktop/tablet/mobile)
- All tests pass

**Effort:** 3 points

---

### Ticket 15: Create Component Library Storybook

**Title:** Document all new UI components in Storybook

**Description:**
Add `.storybook/` config and write stories for all new primitives. Stories document props, variants, states, responsive behavior.

**Files to create:**
- `.storybook/main.ts`
- `.storybook/preview.ts`
- `apps/web/components/ui/Button.stories.tsx`
- `apps/web/components/ui/Card.stories.tsx`
- `apps/web/components/ui/MetricCard.stories.tsx`
- `apps/web/components/ui/Panel.stories.tsx`
- `apps/web/components/ui/Badge.stories.tsx`
- `apps/web/components/shell/Topbar.stories.tsx`

**Acceptance Criteria:**
1. All UI primitives have stories
2. Stories show all variants/states
3. Props documented in story descriptions
4. Responsive behavior testable in Storybook
5. Dark/light theme toggle in Storybook

**Dependencies:**
- All UI component tickets (5-9)

**Testing:**
- Storybook builds successfully
- All stories render
- Props panel shows correct types
- Theme toggle works in stories

**Effort:** 3 points

---

## PHASE 2: FRONTEND STATE CLEANUP (Tickets 16-30)

### Ticket 16: Split API Client Modules

**Title:** Create modular API client layer replacing monolithic `lib/api.ts`

**Description:**
Current `lib/api.ts` is 300+ lines. Split into focused modules:
1. `lib/api/core.ts` — baseURL, apiRequest, auth
2. `lib/api/execution.ts` — execution endpoints
3. `lib/api/analytics.ts` — analytics/market data endpoints
4. `lib/api/signals.ts` — signal endpoints
5. `lib/api/models.ts` — model registry endpoints (new)
6. `lib/api/news.ts` — news endpoints (new)

**Files to create:**
- `apps/web/lib/api/core.ts`
- `apps/web/lib/api/execution.ts`
- `apps/web/lib/api/analytics.ts`
- `apps/web/lib/api/signals.ts`
- `apps/web/lib/api/models.ts`
- `apps/web/lib/api/news.ts`
- `apps/web/lib/api/index.ts` — re-exports all for backward compat

**Files to update:**
- Delete or deprecate `apps/web/lib/api.ts` (keep exports via index.ts)

**Acceptance Criteria:**
1. Each module exports only relevant functions
2. All existing functions available via `lib/api` (index re-exports)
3. No functionality changes, only code organization
4. TypeScript types preserved
5. All current usage still works

**Dependencies:**
- None (refactor only)

**Testing:**
- All API calls still work (no breaking changes)
- Imports work from new modules
- Imports work from `lib/api` (backward compat)
- Type checking passes
- All Playwright tests pass

**Effort:** 3 points

---

### Ticket 17: Create Execution Page Controller Hook

**Title:** Implement `lib/hooks/useExecutionPageController.ts`

**Description:**
Execution page currently has 15+ useState calls. Consolidate into a controller hook that returns:
1. listState (list, loading, error, pagination)
2. detailState (detail, loading, error)
3. historyState (history, loading)
4. positionsState (positions, loading)
5. journalState (journal entries, add/update functions)
6. actions (loadList, loadDetail, loadHistory, saveJournal)
7. filters (statusFilter, assetFilter, setters)
8. url state management (searchParams sync)

**Files to create:**
- `apps/web/lib/hooks/useExecutionPageController.ts`

**Acceptance Criteria:**
1. Hook encapsulates all execution page async logic
2. Returns typed object with clear sections
3. Handles URL param sync (status, asset, executionId)
4. Implements pagination (PAGE_SIZE = 10, offset)
5. Error states captured
6. Loading states tracked

**Dependencies:**
- Ticket 16 (API client split)

**Testing:**
- Hook renders without errors
- List loads correctly
- Detail loads on selection
- URL updates on filter change
- Pagination works (canGoPrev, canGoNext)
- Error handling works
- Unit tests for hook logic

**Effort:** 5 points

---

### Ticket 18: Create Analytics Page Controller Hook

**Title:** Implement `lib/hooks/useAnalyticsPageController.ts`

**Description:**
Analytics page has heavy filtering and aggregation logic. Move to controller hook returning:
1. filters (windowSize, assetFilter, statusFilter, viewMode, showLifecycle, timeRange)
2. filteredData (insights, segments, heatmap, etc.)
3. computedMetrics (summary, statusCards, lifecycle rows)
4. charts (chartSeries, toggleSeries, hiddenSeries)
5. loading/error state

**Files to create:**
- `apps/web/lib/hooks/useAnalyticsPageController.ts`

**Acceptance Criteria:**
1. All filtering logic moved from page to hook
2. Returns memoized computed data
3. Filter changes trigger recalculation
4. Time range filtering works
5. Series toggle works
6. Window size filtering (25/50/100) works

**Dependencies:**
- Ticket 16 (API client split)
- `useExecutionAnalytics` hook (already exists)

**Testing:**
- Hook renders without errors
- Filters update correctly
- Data recalculates on filter change
- Memo optimization works (no unnecessary recalc)
- Unit tests for aggregation logic
- Chart series toggle works

**Effort:** 5 points

---

### Ticket 19: Refactor Execution Page with Controller

**Title:** Update `app/execution/page.tsx` to use `useExecutionPageController`

**Description:**
Replace all inline useState/useEffect/async logic in execution page with controller hook. Page becomes thin orchestrator + JSX.

**Files to update:**
- `apps/web/app/execution/page.tsx` (150+ lines → 60 lines)

**Acceptance Criteria:**
1. Page uses useExecutionPageController hook
2. All state/loading/error/actions come from hook
3. JSX layout unchanged, behavior same
4. No visual changes
5. URL state sync still works
6. Responsive layout unchanged
7. All tests pass

**Dependencies:**
- Ticket 17 (useExecutionPageController)

**Testing:**
- All execution features work (list, detail, journal, history)
- URL params persist
- Pagination works
- Filter changes work
- Visual snapshots match before
- All Playwright tests pass

**Effort:** 3 points

---

### Ticket 20: Refactor Analytics Page with Controller

**Title:** Update `app/analytics/page.tsx` to use `useAnalyticsPageController`

**Description:**
Replace inline state/computed logic in analytics page with controller hook. Page becomes thin JSX wrapper.

**Files to update:**
- `apps/web/app/analytics/page.tsx` (300+ lines → 100 lines)

**Acceptance Criteria:**
1. Page uses useAnalyticsPageController hook
2. All aggregations/filters delegated to hook
3. JSX layout unchanged
4. No visual changes
5. All filter interactions work
6. Chart updates work

**Dependencies:**
- Ticket 18 (useAnalyticsPageController)

**Testing:**
- All analytics features work (filters, views, lifecycle, drilldown)
- Data aggregation correct
- Chart series toggle works
- Time range filtering works
- Visual snapshots match
- All tests pass

**Effort:** 3 points

---

### Ticket 21: Create State Management Layer

**Title:** Implement reducer-based state for complex pages

**Description:**
Create reducer functions for pages with multiple coordinated state updates:
1. `lib/state/analyticsReducer.ts` — filter/view/drilldown actions
2. `lib/state/executionReducer.ts` — list/detail/journal/pagination actions

**Files to create:**
- `apps/web/lib/state/analyticsReducer.ts`
- `apps/web/lib/state/executionReducer.ts`

**Acceptance Criteria:**
1. Reducer handles all filter/pagination actions
2. Action types clearly named (SET_FILTER, RESET, etc.)
3. State shape documented in JSDoc
4. Type safety with TypeScript
5. No side effects in reducer (pure functions)

**Dependencies:**
- None

**Testing:**
- Reducer unit tests
- All action types tested
- State transitions correct
- Type checking passes

**Effort:** 3 points

---

### Ticket 22: Convert useExecutionPageController to use Reducer

**Title:** Refactor `useExecutionPageController` to use `executionReducer`

**Description:**
Simplify controller hook by using reducer for state management:
1. Update hook to use `useReducer` + `executionReducer`
2. Actions (setFilter, setPagination, etc.) dispatch to reducer
3. Cleaner state management

**Files to update:**
- `apps/web/lib/hooks/useExecutionPageController.ts`

**Acceptance Criteria:**
1. Hook uses useReducer internally
2. Actions dispatch to reducer
3. External API unchanged (backward compat)
4. All functionality preserved
5. Cleaner state updates

**Dependencies:**
- Ticket 21 (executionReducer)

**Testing:**
- Hook behavior unchanged
- Page still works correctly
- All tests pass
- No visual changes

**Effort:** 2 points

---

### Ticket 23: Convert useAnalyticsPageController to use Reducer

**Title:** Refactor `useAnalyticsPageController` to use `analyticsReducer`

**Description:**
Simplify analytics controller using reducer pattern.

**Files to update:**
- `apps/web/lib/hooks/useAnalyticsPageController.ts`

**Acceptance Criteria:**
1. Hook uses useReducer internally
2. All filter/view actions dispatch to reducer
3. External API unchanged
4. All functionality preserved

**Dependencies:**
- Ticket 21 (analyticsReducer)

**Testing:**
- Hook behavior unchanged
- Page works correctly
- All tests pass

**Effort:** 2 points

---

### Ticket 24: Create Query Client / React Query Setup

**Title:** Optional: Set up React Query for API state management

**Description:**
(Optional for Phase 2; can defer to Phase 3)

Add React Query for simplified API data fetching, caching, background updates. Update API hooks to use `useQuery`/`useMutation`.

**Files to create:**
- `apps/web/lib/query/client.ts`
- `apps/web/lib/query/execution.ts`
- `apps/web/lib/query/analytics.ts`

**Files to update:**
- `app/layout.tsx` — add QueryClientProvider

**Acceptance Criteria:**
1. React Query client configured
2. useQuery hooks for GET requests
3. useMutation hooks for POST/PUT requests
4. Caching strategy defined (staleTime, cacheTime)
5. Loading/error/data states managed by React Query
6. Backward compat: existing hooks still work if not using Query

**Dependencies:**
- None (can be done in parallel)

**Testing:**
- Query client initializes
- useQuery works for data fetching
- useMutation works for updates
- Caching works
- Stale state refreshes
- All tests pass

**Effort:** 4 points (optional)

---

### Ticket 25: Add Visual Regression Testing

**Title:** Create Playwright visual snapshots for all pages

**Description:**
Add visual regression tests for dashboard, analytics, execution, models pages at multiple viewports and themes.

**Files to create:**
- `apps/web/tests/visual.spec.ts`

**Acceptance Criteria:**
1. Snapshots for dashboard (390px, 768px, 1024px, dark/light)
2. Snapshots for analytics (390px, 768px, 1024px, dark/light)
3. Snapshots for execution (390px, 768px, 1024px, dark/light)
4. All snapshots committed to repo
5. CI compares new snapshots to baseline

**Dependencies:**
- Tickets 1-20 (pages should be refactored)

**Testing:**
- Visual tests run
- No visual diffs vs expected
- Mobile/tablet/desktop snapshots all pass

**Effort:** 3 points

---

### Ticket 26: Update E2E Tests

**Title:** Verify all Playwright tests pass with new architecture

**Description:**
Run existing Playwright tests against refactored pages. Update selectors/assertions if needed.

**Files to update:**
- `apps/web/tests/smoke.spec.ts`
- `apps/web/tests/regression.spec.ts`
- `apps/web/tests/responsive.spec.ts`

**Acceptance Criteria:**
1. All 66 existing Playwright tests pass
2. No selector breakages
3. All page interactions work
4. Dark/light theme tests pass
5. Responsive tests pass (390/768/1024px)

**Dependencies:**
- Tickets 1-25 (all refactors complete)

**Testing:**
- Full Playwright suite runs
- 66/66 tests passing
- No visual regressions
- No flaky tests

**Effort:** 2 points

---

### Ticket 27: Create Shared UI Token Package

**Title:** Create `packages/shared-ui-tokens` for design system export

**Description:**
Extract color, spacing, typography tokens into a shared TypeScript package so learning app and other services can reference the same design values.

**Files to create:**
- `packages/shared-ui-tokens/package.json`
- `packages/shared-ui-tokens/src/colors.ts`
- `packages/shared-ui-tokens/src/spacing.ts`
- `packages/shared-ui-tokens/src/typography.ts`
- `packages/shared-ui-tokens/src/index.ts`
- `packages/shared-ui-tokens/tsconfig.json`

**Acceptance Criteria:**
1. Colors: all CSS variable equivalents exported as constants
2. Spacing: scale (4px, 8px, 12px, 16px, 20px, 24px, etc.)
3. Typography: sizes (12px, 14px, 16px, 18px, 20px, etc.), weights (400, 500, 700)
4. Dark/light theme variants
5. No hardcoded values in web app; all reference this package

**Dependencies:**
- None (can create in parallel)

**Testing:**
- Package builds
- Types exported correctly
- Values match CSS variables
- Can import in web and learning apps

**Effort:** 2 points

---

### Ticket 28: Create Shared Config Package

**Title:** Create `packages/shared-config` for common constants

**Description:**
Create shared config package for scoring buckets, risk profiles, execution modes, universe definitions.

**Files to create:**
- `packages/shared-config/package.json`
- `packages/shared-config/src/scoring-buckets.ts`
- `packages/shared-config/src/risk-profiles.ts`
- `packages/shared-config/src/execution-modes.ts`
- `packages/shared-config/src/index.ts`

**Acceptance Criteria:**
1. Scoring buckets: asset_class, strategy, timeframe, liquidity, regime
2. Risk profiles: thresholds, limits, parameters
3. Execution modes: paper, confirm_live, auto_live
4. Shared between frontend + backend (via API contracts)
5. Well-documented

**Dependencies:**
- None

**Testing:**
- Package builds
- Constants exported
- Can import in web and API

**Effort:** 2 points

---

### Ticket 29: Create Shared Types Package

**Title:** Create `packages/shared-types` for TypeScript interfaces

**Description:**
Extract shared TypeScript types used by frontend and backend into a monorepo package: Signal, Position, RiskDecision, ScoredOpportunity, etc.

**Files to create:**
- `packages/shared-types/package.json`
- `packages/shared-types/src/signal.ts`
- `packages/shared-types/src/execution.ts`
- `packages/shared-types/src/scoring.ts`
- `packages/shared-types/src/models.ts`
- `packages/shared-types/src/index.ts`

**Acceptance Criteria:**
1. Signal interface (matches backend SignalOutput)
2. Execution types (status, side, etc.)
3. Scoring types (RankedOpportunity, ScoredOpportunity)
4. Model types (ModelVersion, ModelPromotion)
5. All used in both web and API

**Dependencies:**
- None

**Testing:**
- Package builds
- Types exported
- No conflicts with existing types
- Can import in both web/api

**Effort:** 2 points

---

### Ticket 30: Integration Test: Full Page Flow

**Title:** E2E test: Dashboard → Execution → Analytics → Models flow

**Description:**
Write an E2E test covering a full user flow: view dashboard, open execution detail, check analytics, view model info. Validates all refactoring didn't break integration.

**Files to create:**
- `apps/web/tests/full-flow.spec.ts`

**Acceptance Criteria:**
1. Test opens dashboard, verifies metrics
2. Navigates to execution page
3. Filters executions, opens detail
4. Saves journal entry
5. Navigates to analytics
6. Applies filters, checks charts
7. Navigates to models page (scaffold OK for Phase 1)
8. All interactions work, no errors

**Dependencies:**
- Tickets 1-29 (all phase 1-2 work complete)

**Testing:**
- Test runs successfully
- All page transitions work
- Data persists across navigations
- No console errors

**Effort:** 3 points

---

## Summary

| Ticket | Title | Phase | Effort | Status |
|--------|-------|-------|--------|--------|
| 1-15 | Frontend Shell Modernization | 1 | 40 pts | 📋 Planned |
| 16-30 | Frontend State Cleanup | 2 | 45 pts | 📋 Planned |

**Total Phase 1-2 effort:** ~85 story points  
**Timeline:** 2-3 weeks (2-week sprints with 25-30 points/week velocity)

**Next steps after Phase 2:**
- Phase 3: Backend runtime cleanup (scoring split, config, deprecations)
- Phase 4: Data model expansion (governance, regime, features, opportunities)
- Phases 5-13: Provider adapters, backfill, learning, training, governance, UI, monitoring

---

**All tickets linked to ANTI_DRIFT.md rules and RELEASE_GATES.md.**

