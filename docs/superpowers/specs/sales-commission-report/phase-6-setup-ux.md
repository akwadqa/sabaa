# Sales Commission Report – Phase 6: Client setup UX

> Read `plan-overview.md` first: it holds the global constraints, review focus and file map that apply to every task here.

### Task 12: Commission Setup page and guided forms

**Files:**
- Create: Desk Page `sabaa/sabaa/page/commission_setup/` (`commission_setup.json`, `.js`, `.css` small), roles Commission Manager
- Create: `sabaa/sabaa/doctype/commission_rule/commission_rule.js`, `sabaa/sabaa/doctype/commission_plan/commission_plan.js`, `sabaa/public/js/commission/people_dialog.js`, `sabaa/public/js/commission/missing_figures_dialog.js` (bundled via `app_include_js` only if Page/form need them, else `frappe.require`)
- Modify: `sabaa/sabaa/workspace/` — add a shortcut "Commission Setup" and the report to the existing Sabaa workspace
- Test: `sabaa/sabaa/commission/tests/test_api_ui.py` (server side of each dialog)

**Interfaces:**
- Consumes: `api.get_setup_status`, `api.preview_tier`, `api.get_people`, `api.save_people`, `api.get_missing_figure_grid`, `api.save_missing_figures`, `api.copy_plan`, `default_plan.create_default_plan`, `templates.get_templates`.
- Behaviour (spec §6.5, copy exact):
  - Page header: Plan and Month fields; primary button "Check setup"; it runs on load. Empty state when no plan: "No commission plan yet." + primary "Create default plan".
  - Body: groups by category; each rule row = name, status indicator, summary line, then problems as "<message> → Fix". Fix opens the doc (`frappe.set_route`) or the People / Missing figures dialog.
  - Secondary actions: "Copy plan to new period" (dialog: new name, from, to), "Open report" (route to the report with plan and month).
  - Rule form: "New rule" from a plan opens a template picker dialog (grouped by category). Tier grid row label formatter: "From 70,000 QAR → 200 QAR (+3.5% above)". "Try an amount" Currency field in the Tiers section showing `preview_tier` result text: "120,000 → Tier 3 of 5 → 1,050 QAR" and, with scaling, "Target for 9 drivers: 900,000".
  - People dialog: table of members with a source badge, Exclude toggle, Share % for pools, "Add assistant" (employee + salesman); live footer "100% ✓" or "95%, 5% missing"; Save disabled while shares are not 100%.
  - Missing figures dialog: grid rows = sales persons/Company, columns = missing months; a "Paste from Excel" textarea that parses tab-separated rows.

- [ ] **Step 1: Failing tests (server):** `get_setup_status` returns 12 rows for the default plan with statuses; `save_people` with Exclude row creates an Exclude assignment from the month start; `save_people` with shares 95% raises "Shares total 95%. They must total 100%."; `save_missing_figures` round-trips through `get_missing_figure_grid`.
- [ ] **Step 2–4:** FAIL → implement page, dialogs and form scripts → PASS; `bench build --app sabaa` succeeds.
- [ ] **Step 5: Browser check with agent-browser** (spec §6.5 UX acceptance): on a fresh test plan, create default plan → fix Smile24 problems via Fix links → Smile24 rule shows Ready, without opening a list view or Advanced. Every problem has a working Fix link. "Try an amount" value equals the report Detail amount for the same basis. Take screenshots into the scratchpad. Run the `ui-design` review checklist and fix findings.
- [ ] **Step 6: Commit** — `feat(commission): add commission setup page and guided forms`
