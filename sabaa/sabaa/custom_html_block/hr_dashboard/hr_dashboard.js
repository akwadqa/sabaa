/**
 * HR Dashboard – Custom HTML Block script (ERPNext / HRMS v15).
 *
 * - `root_element` is the block's shadow root, injected by Frappe.
 * - Read-only: every figure comes from frappe.client.get_list, so user permissions apply.
 * - Bilingual: follows the user's language (Arabic = RTL) with a manual toggle; labels live in AR below.
 * - Class names: Frappe injects desk.bundle.css into the shadow root, so avoid Bootstrap names (.col, .pill, .row, .card).
 * - Layout: SECTIONS holds one entry per tab, each with load() (fetch once, cached) and render() (pure HTML).
 */
(async function () {
  const root = root_element;
  const $ = (selector) => root.querySelector(selector);
  const esc = (s) => frappe.utils.escape_html(String(s == null ? "" : s));

  // ---------- Language ----------
  // Keys are the English labels; data values (statuses, document types) are translated from the same map.
  const AR = {
    "HR Dashboard": "لوحة معلومات الموارد البشرية",
    "All Companies": "كل الشركات",
    "All Departments": "كل الأقسام",
    "This Month": "هذا الشهر",
    "This Quarter": "هذا الربع",
    "This Year": "هذه السنة",
    "Last 12 Months": "آخر 12 شهراً",
    "Employee Lifecycle": "دورة حياة الموظف",
    Leaves: "الإجازات",
    "Official Papers": "الأوراق الرسمية",
    Payroll: "الرواتب",
    "Advances & Claims": "السلف والمطالبات",
    Recruitment: "التوظيف",
    "Loading...": "جارٍ التحميل...",
    "No data": "لا توجد بيانات",
    "Not available (no permission or module not in use)": "غير متاح (لا توجد صلاحية أو الوحدة غير مستخدمة)",
    "Not Set": "غير محدد",
    Updated: "آخر تحديث",
    "Figures follow your permissions": "الأرقام حسب صلاحياتك",
    "Active Employees": "الموظفون على رأس العمل",
    "New Hires": "التعيينات الجديدة",
    Exits: "المغادرون",
    "Onboarding in Progress": "تهيئة قيد التنفيذ",
    "Separations in Progress": "إنهاء خدمة قيد التنفيذ",
    Promotions: "الترقيات",
    Transfers: "التنقلات",
    "Returning from Vacation (30 days)": "العائدون من الإجازة (30 يوماً)",
    "Headcount by Department": "عدد الموظفين حسب القسم",
    "Headcount by Nationality": "عدد الموظفين حسب الجنسية",
    "Headcount by Sponsorship": "عدد الموظفين حسب الكفالة",
    "Headcount by Place of Work": "عدد الموظفين حسب مكان العمل",
    "Headcount by Employment Type": "عدد الموظفين حسب نوع التوظيف",
    "Hires vs Exits (12 months)": "التعيينات مقابل المغادرين (12 شهراً)",
    Hires: "تعيينات",
    "Returning from Vacation": "العائدون من الإجازة",
    Employee: "الموظف",
    Department: "القسم",
    "Return Date": "تاريخ العودة",
    "On Leave Today": "في إجازة اليوم",
    "Pending Approval": "بانتظار الاعتماد",
    "Leave Days Taken": "أيام الإجازة المستخدمة",
    "Leave Applications": "طلبات الإجازة",
    "Days by Leave Type": "الأيام حسب نوع الإجازة",
    "Taken vs Allocated": "المستخدم مقابل المخصص",
    "Leave Days per Month": "أيام الإجازة شهرياً",
    "Leave Type": "نوع الإجازة",
    From: "من",
    To: "إلى",
    Days: "الأيام",
    Expired: "منتهية",
    "Within 30 Days": "خلال 30 يوماً",
    "31–60 Days": "31–60 يوماً",
    "61–90 Days": "61–90 يوماً",
    "Contracts Ending (90 days)": "عقود تنتهي (90 يوماً)",
    "Expiring by Document Type": "المنتهية والقريبة حسب نوع المستند",
    "Documents Expired or Expiring": "مستندات منتهية أو قريبة الانتهاء",
    Document: "المستند",
    "Reference No": "رقم المرجع",
    "Expiry Date": "تاريخ الانتهاء",
    "Days Left": "الأيام المتبقية",
    "Last Payroll Net Pay": "صافي آخر مسير رواتب",
    "Gross Pay": "إجمالي الرواتب",
    Deductions: "الاستقطاعات",
    "Salary Slips": "قسائم الرواتب",
    draft: "مسودة",
    submitted: "معتمدة",
    "Net Pay per Month": "صافي الرواتب شهرياً",
    "Net Pay by Department": "صافي الرواتب حسب القسم",
    "Outstanding Advances": "السلف القائمة",
    "Advances Awaiting Payment": "سلف بانتظار الصرف",
    "Claims Pending Approval": "مطالبات بانتظار الاعتماد",
    "Unpaid Claims": "مطالبات غير مدفوعة",
    "Claimed in Period": "المطالبات خلال الفترة",
    "Claims by Type": "المطالبات حسب النوع",
    "Outstanding Advances by Employee": "السلف القائمة حسب الموظف",
    "Open Positions": "الوظائف الشاغرة",
    Applicants: "المتقدمون",
    "Interviews Pending": "مقابلات قيد الانتظار",
    "Offers Awaiting Response": "عروض بانتظار الرد",
    "Offers Accepted": "عروض مقبولة",
    "Applicants by Status": "المتقدمون حسب الحالة",
    "Offers by Status": "العروض حسب الحالة",
    "Open Positions by Department": "الشواغر حسب القسم",
    "Hiring Funnel": "مسار التوظيف",
    Interviews: "المقابلات",
    Offers: "العروض",
    Accepted: "مقبول",
    // Data values
    Open: "مفتوح",
    Approved: "معتمد",
    Rejected: "مرفوض",
    Cancelled: "ملغي",
    Replied: "تم الرد",
    Hold: "معلّق",
    "Awaiting Response": "بانتظار الرد",
    Pending: "قيد الانتظار",
    Draft: "مسودة",
    Paid: "مدفوع",
    Unpaid: "غير مدفوع",
    "Under Review": "قيد المراجعة",
    Cleared: "مجتاز",
    Passport: "جواز السفر",
    QID: "البطاقة الشخصية (QID)",
    "Health Insurance": "التأمين الصحي",
    "Health Card": "البطاقة الصحية",
    "Driving License": "رخصة القيادة",
    Visa: "التأشيرة",
  };
  let lang = String((frappe.boot && frappe.boot.lang) || "en").startsWith("ar") ? "ar" : "en";
  const t = (k) => (lang === "ar" ? AR[k] || k : k);
  const tv = (v) => (!v ? t("Not Set") : lang === "ar" ? AR[v] || __(v) : v);

  // ---------- Date, number and data helpers ----------
  const TODAY = frappe.datetime.get_today();
  const toDate = (s) => new Date(String(s).slice(0, 10) + "T00:00:00");
  const iso = (d) =>
    d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  const addDays = (s, n) => {
    const d = toDate(s);
    d.setDate(d.getDate() + n);
    return iso(d);
  };
  const daysTo = (s) => Math.round((toDate(s) - toDate(TODAY)) / 864e5);
  const ym = (s) => String(s || "").slice(0, 7);
  const MONTHS = (() => {
    const d = toDate(TODAY),
      o = [];
    for (let i = 11; i >= 0; i--) o.push(iso(new Date(d.getFullYear(), d.getMonth() - i, 1)).slice(0, 7));
    return o;
  })();
  const SINCE = MONTHS[0] + "-01";
  const monthLabel = (m) => {
    const p = m.split("-");
    return new Date(+p[0], +p[1] - 1, 1).toLocaleDateString(lang === "ar" ? "ar-u-nu-latn" : "en", { month: "short" });
  };
  const nf = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const CUR = (frappe.boot && frappe.boot.sysdefaults && frappe.boot.sysdefaults.currency) || "";
  const num = (v) => nf.format(+v || 0);
  const money = (v) => (num(v) + " " + CUR).trim();
  const sum = (rows, f) => rows.reduce((a, r) => a + (+f(r) || 0), 0);
  const group = (rows, keyFn, valFn) => {
    const m = new Map();
    rows.forEach((r) => {
      const k = keyFn(r) || "";
      m.set(k, (m.get(k) || 0) + (valFn ? +valFn(r) || 0 : 1));
    });
    return [...m.entries()].map(([label, value]) => ({ label, value })).sort((a, b) => b.value - a.value);
  };
  const api = async (method, args) => {
    const qs = new URLSearchParams();
    Object.entries(args).forEach(([k, v]) => qs.set(k, typeof v === "object" ? JSON.stringify(v) : v));
    const r = await fetch("/api/method/" + method + "?" + qs.toString(), { headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    return (await r.json()).message;
  };
  // Returns rows, or null when the user has no access or the DocType / a field does not exist.
  const getList = async (doctype, fields, filters, extra) => {
    try {
      return (
        (await api(
          "frappe.client.get_list",
          Object.assign({ doctype, fields, filters: filters || [], limit_page_length: 5000 }, extra || {}),
        )) || []
      );
    } catch (e) {
      return null;
    }
  };

  // ---------- State and filters ----------
  const state = { company: "", department: "", period: "year", tab: "life" };
  let EMPS = [],
    EMP = {},
    cache = {};
  const PERIODS = [
    ["month", "This Month"],
    ["quarter", "This Quarter"],
    ["year", "This Year"],
    ["last12", "Last 12 Months"],
  ];
  // [from, to] of the selected period, as ISO dates.
  const period = () => {
    const d = toDate(TODAY),
      y = d.getFullYear(),
      m = d.getMonth();
    if (state.period === "month") return [iso(new Date(y, m, 1)), iso(new Date(y, m + 1, 0))];
    if (state.period === "quarter") {
      const q = Math.floor(m / 3) * 3;
      return [iso(new Date(y, q, 1)), iso(new Date(y, q + 3, 0))];
    }
    if (state.period === "last12") return [addDays(TODAY, -365), TODAY];
    return [y + "-01-01", y + "-12-31"];
  };
  const inP = (s) => {
    if (!s) return false;
    const p = period(),
      x = String(s).slice(0, 10);
    return x >= p[0] && x <= p[1];
  };
  // Company / department filter, resolved through the employee where the row has one.
  const passes = (row) => {
    const e = EMP[row.employee];
    const c = (e && e.company) || row.company,
      d = (e && e.department) || row.department;
    return (!state.company || !c || c === state.company) && (!state.department || d === state.department);
  };
  const ename = (id) => (EMP[id] && EMP[id].employee_name) || id || "";

  // ---------- HTML builders ----------
  const card = (label, value, o) => {
    o = o || {};
    return (
      '<div class="kpi ' +
      (o.tone || "") +
      (o.route ? " link" : "") +
      '"' +
      (o.route ? ' data-route="' + esc(JSON.stringify(o.route)) + '"' : "") +
      ">" +
      '<div class="kpi-v">' +
      esc(value) +
      '</div><div class="kpi-l">' +
      esc(t(label)) +
      "</div>" +
      (o.sub ? '<div class="kpi-s">' + esc(o.sub) + "</div>" : "") +
      "</div>"
    );
  };
  const panel = (title, inner) => '<div class="panel"><h4>' + esc(t(title)) + "</h4>" + inner + "</div>";
  const empty = () => '<div class="empty">' + esc(t("No data")) + "</div>";
  const bars = (title, items, o) => {
    o = o || {};
    items = items.filter((i) => i.value || i.max).slice(0, o.limit || 10);
    if (!items.length) return panel(title, empty());
    const top =
      Math.max.apply(
        null,
        items.map((i) => i.max || i.value),
      ) || 1;
    return panel(
      title,
      items
        .map(
          (i) =>
            '<div class="bar-row"><div class="bar-l" title="' +
            esc(tv(i.label)) +
            '">' +
            esc(tv(i.label)) +
            '</div><div class="bar-t"><div class="bar-f ' +
            (o.cls || "") +
            '" style="width:' +
            Math.max(2, Math.round((i.value / top) * 100)) +
            '%"></div></div><div class="bar-v">' +
            esc(i.text || (o.money ? money(i.value) : num(i.value))) +
            "</div></div>",
        )
        .join(""),
    );
  };
  const cols = (title, series) => {
    const top =
      Math.max.apply(
        null,
        series.map((s) => Math.max.apply(null, s.values)),
      ) || 0;
    if (!top) return panel(title, empty());
    const body = MONTHS.map(
      (m, i) =>
        '<div class="hrd-col"><div class="hrd-col-b">' +
        series
          .map(
            (s, k) =>
              '<div class="hrd-col-f ' +
              (k ? "s2" : "") +
              '" style="height:' +
              Math.round((s.values[i] / top) * 100) +
              '%" title="' +
              esc(t(s.name) + ": " + num(s.values[i])) +
              '"></div>',
          )
          .join("") +
        '</div><div class="hrd-col-x">' +
        esc(monthLabel(m)) +
        "</div></div>",
    ).join("");
    const legend =
      series.length > 1
        ? '<div class="legend">' +
          series.map((s, k) => '<span><i class="' + (k ? "s2" : "") + '"></i>' + esc(t(s.name)) + "</span>").join("") +
          "</div>"
        : "";
    return panel(title, '<div class="hrd-cols">' + body + "</div>" + legend);
  };
  const byMonth = (rows, dateFn, valFn) =>
    MONTHS.map((m) =>
      sum(
        rows.filter((r) => ym(dateFn(r)) === m),
        valFn || (() => 1),
      ),
    );
  const table = (title, heads, rows) =>
    panel(
      title,
      !rows.length
        ? empty()
        : '<div class="tbl-wrap"><table class="tbl"><thead><tr>' +
            heads.map((h) => "<th>" + esc(t(h)) + "</th>").join("") +
            "</tr></thead><tbody>" +
            rows.map((r) => "<tr>" + r.map((c) => "<td>" + c + "</td>").join("") + "</tr>").join("") +
            "</tbody></table></div>",
    );
  const na = () =>
    '<div class="panel"><div class="empty">' + esc(t("Not available (no permission or module not in use)")) + "</div></div>";
  const grid = (cls, items) => '<div class="grid ' + cls + '">' + items.join("") + "</div>";

  // ---------- Sections (one per tab) ----------
  const SECTIONS = {
    life: {
      title: "Employee Lifecycle",
      load: async () => ({
        onb: await getList(
          "Employee Onboarding",
          ["name", "boarding_status", "company", "department", "docstatus"],
          [["docstatus", "<", 2]],
        ),
        sep: await getList(
          "Employee Separation",
          ["name", "employee", "boarding_status", "company", "department", "docstatus"],
          [["docstatus", "<", 2]],
        ),
        pro: await getList(
          "Employee Promotion",
          ["name", "employee", "promotion_date"],
          [
            ["docstatus", "=", 1],
            ["promotion_date", ">=", SINCE],
          ],
        ),
        tra: await getList(
          "Employee Transfer",
          ["name", "employee", "transfer_date"],
          [
            ["docstatus", "=", 1],
            ["transfer_date", ">=", SINCE],
          ],
        ),
      }),
      render: (d) => {
        const emps = EMPS.filter(passes),
          act = emps.filter((e) => e.status === "Active"),
          p = period();
        const hires = emps.filter((e) => inP(e.date_of_joining)),
          exits = emps.filter((e) => inP(e.relieving_date));
        const back = act
          .filter(
            (e) =>
              e.custom_return_from_vacation &&
              e.custom_return_from_vacation >= TODAY &&
              e.custom_return_from_vacation <= addDays(TODAY, 30),
          )
          .sort((a, b) => (a.custom_return_from_vacation > b.custom_return_from_vacation ? 1 : -1));
        const inProgress = (rows) => (rows || []).filter((r) => passes(r) && r.boarding_status !== "Completed").length;
        return (
          grid("g-kpi", [
            card("Active Employees", num(act.length), { route: ["Employee", { status: "Active" }] }),
            card("New Hires", num(hires.length), { tone: "green", route: ["Employee", { date_of_joining: ["between", p] }] }),
            card("Exits", num(exits.length), { tone: "red", route: ["Employee", { relieving_date: ["between", p] }] }),
            card("Onboarding in Progress", num(inProgress(d.onb)), { tone: "amber", route: ["Employee Onboarding", {}] }),
            card("Separations in Progress", num(inProgress(d.sep)), { tone: "amber", route: ["Employee Separation", {}] }),
            card("Promotions", num((d.pro || []).filter((r) => passes(r) && inP(r.promotion_date)).length), {
              tone: "gray",
              route: ["Employee Promotion", {}],
            }),
            card("Transfers", num((d.tra || []).filter((r) => passes(r) && inP(r.transfer_date)).length), {
              tone: "gray",
              route: ["Employee Transfer", {}],
            }),
            card("Returning from Vacation (30 days)", num(back.length), { tone: "gray" }),
          ]) +
          grid("g-2", [
            cols("Hires vs Exits (12 months)", [
              { name: "Hires", values: byMonth(emps, (e) => e.date_of_joining) },
              { name: "Exits", values: byMonth(emps, (e) => e.relieving_date) },
            ]),
            bars(
              "Headcount by Department",
              group(act, (e) => e.department),
            ),
            bars(
              "Headcount by Nationality",
              group(act, (e) => e.nationality),
              { cls: "b2" },
            ),
            bars(
              "Headcount by Employment Type",
              group(act, (e) => e.employment_type),
              { cls: "b3" },
            ),
            bars(
              "Headcount by Sponsorship",
              group(act, (e) => e.sponsorship),
              { cls: "b2" },
            ),
            bars(
              "Headcount by Place of Work",
              group(act, (e) => e.place_of_work),
            ),
          ]) +
          grid("", [
            table(
              "Returning from Vacation",
              ["Employee", "Department", "Return Date"],
              back.slice(0, 30).map((e) => [esc(e.employee_name), esc(e.department || ""), esc(e.custom_return_from_vacation)]),
            ),
          ])
        );
      },
    },
    leave: {
      title: "Leaves",
      load: async () => ({
        app: await getList(
          "Leave Application",
          ["name", "employee", "leave_type", "from_date", "to_date", "total_leave_days", "status", "docstatus"],
          [
            ["docstatus", "<", 2],
            ["to_date", ">=", SINCE],
          ],
        ),
        alloc: await getList(
          "Leave Allocation",
          ["employee", "leave_type", "total_leaves_allocated", "from_date"],
          [
            ["docstatus", "=", 1],
            ["from_date", "<=", TODAY],
            ["to_date", ">=", TODAY],
          ],
        ),
      }),
      render: (d) => {
        if (!d.app) return na();
        const app = d.app.filter(passes),
          ok = app.filter((r) => r.docstatus === 1 && r.status === "Approved");
        const today = ok.filter((r) => r.from_date <= TODAY && r.to_date >= TODAY);
        const pend = app.filter((r) => r.docstatus === 0 && r.status === "Open"),
          inp = ok.filter((r) => inP(r.from_date));
        const alloc = (d.alloc || []).filter(passes);
        const bal = group(
          alloc,
          (r) => r.leave_type,
          (r) => r.total_leaves_allocated,
        ).map((a) => {
          const start = alloc
            .filter((r) => r.leave_type === a.label)
            .map((r) => r.from_date)
            .sort()[0];
          const used = sum(
            ok.filter((r) => r.leave_type === a.label && r.from_date >= start),
            (r) => r.total_leave_days,
          );
          return { label: a.label, value: used, max: a.value, text: num(used) + " / " + num(a.value) };
        });
        return (
          grid("g-kpi", [
            card("On Leave Today", num(today.length), {
              route: ["Leave Application", { status: "Approved", from_date: ["<=", TODAY], to_date: [">=", TODAY] }],
            }),
            card("Pending Approval", num(pend.length), { tone: "amber", route: ["Leave Application", { status: "Open" }] }),
            card("Leave Days Taken", num(sum(inp, (r) => r.total_leave_days)), { tone: "gray" }),
            card("Leave Applications", num(app.filter((r) => inP(r.from_date)).length), { tone: "gray" }),
          ]) +
          grid("g-2", [
            cols("Leave Days per Month", [
              {
                name: "Days",
                values: byMonth(
                  ok,
                  (r) => r.from_date,
                  (r) => r.total_leave_days,
                ),
              },
            ]),
            bars(
              "Days by Leave Type",
              group(
                inp,
                (r) => r.leave_type,
                (r) => r.total_leave_days,
              ),
            ),
            bars("Taken vs Allocated", bal, { cls: "b3" }),
          ]) +
          grid("", [
            table(
              "On Leave Today",
              ["Employee", "Leave Type", "From", "To", "Days"],
              today.map((r) => [
                esc(ename(r.employee)),
                esc(tv(r.leave_type)),
                esc(r.from_date),
                esc(r.to_date),
                esc(num(r.total_leave_days)),
              ]),
            ),
          ])
        );
      },
    },
    papers: {
      title: "Official Papers",
      load: async () => ({
        ref: await getList(
          "Employee Reference",
          ["name", "employee", "document", "reference_no", "expiry_date"],
          [
            ["is_current", "=", 1],
            ["expiry_date", "is", "set"],
            ["expiry_date", "<=", addDays(TODAY, 90)],
          ],
          { order_by: "expiry_date asc" },
        ),
      }),
      render: (d) => {
        if (!d.ref) return na();
        const rows = d.ref
          .filter((r) => passes(r) && (!EMP[r.employee] || EMP[r.employee].status === "Active"))
          .map((r) => Object.assign({ left: daysTo(r.expiry_date) }, r));
        const b = (lo, hi) => rows.filter((r) => r.left >= lo && r.left <= hi);
        const exp = rows.filter((r) => r.left < 0),
          end90 = addDays(TODAY, 90);
        const contracts = EMPS.filter(
          (e) =>
            passes(e) &&
            e.status === "Active" &&
            e.contract_end_date &&
            e.contract_end_date >= TODAY &&
            e.contract_end_date <= end90,
        );
        const pill = (n) =>
          '<span class="hrd-pill ' + (n < 0 ? "red" : n <= 30 ? "amber" : "green") + '">' + esc(num(n)) + "</span>";
        const rt = (a, z) => ["Employee Reference", { is_current: 1, expiry_date: ["between", [a, z]] }];
        return (
          grid("g-kpi", [
            card("Expired", num(exp.length), {
              tone: "red",
              route: ["Employee Reference", { is_current: 1, expiry_date: ["<", TODAY] }],
            }),
            card("Within 30 Days", num(b(0, 30).length), { tone: "amber", route: rt(TODAY, addDays(TODAY, 30)) }),
            card("31–60 Days", num(b(31, 60).length), { route: rt(addDays(TODAY, 31), addDays(TODAY, 60)) }),
            card("61–90 Days", num(b(61, 90).length), { tone: "green", route: rt(addDays(TODAY, 61), end90) }),
            card("Contracts Ending (90 days)", num(contracts.length), {
              tone: "gray",
              route: ["Employee", { status: "Active", contract_end_date: ["between", [TODAY, end90]] }],
            }),
          ]) +
          grid("g-2", [
            bars(
              "Expiring by Document Type",
              group(rows, (r) => r.document),
              { cls: "b4" },
            ),
          ]) +
          grid("", [
            table(
              "Documents Expired or Expiring",
              ["Employee", "Document", "Reference No", "Expiry Date", "Days Left"],
              rows
                .slice(0, 60)
                .map((r) => [
                  esc(ename(r.employee)),
                  esc(tv(r.document)),
                  esc(r.reference_no || ""),
                  esc(r.expiry_date),
                  pill(r.left),
                ]),
            ),
          ])
        );
      },
    },
    payroll: {
      title: "Payroll",
      load: async () => ({
        ss: await getList(
          "Salary Slip",
          ["name", "employee", "department", "company", "end_date", "gross_pay", "total_deduction", "net_pay", "docstatus"],
          [
            ["docstatus", "<", 2],
            ["end_date", ">=", SINCE],
          ],
        ),
      }),
      render: (d) => {
        if (!d.ss) return na();
        const ss = d.ss.filter(passes),
          last = ss
            .map((r) => ym(r.end_date))
            .sort()
            .pop(),
          cur = ss.filter((r) => ym(r.end_date) === last);
        const sub = last ? monthLabel(last) + " " + last.slice(0, 4) : "";
        return (
          grid("g-kpi", [
            card("Last Payroll Net Pay", money(sum(cur, (r) => r.net_pay)), { sub, route: ["Salary Slip", {}] }),
            card("Gross Pay", money(sum(cur, (r) => r.gross_pay)), { tone: "green", sub }),
            card("Deductions", money(sum(cur, (r) => r.total_deduction)), { tone: "red", sub }),
            card("Salary Slips", num(cur.length), {
              tone: "gray",
              sub:
                num(cur.filter((r) => r.docstatus === 1).length) +
                " " +
                t("submitted") +
                " · " +
                num(cur.filter((r) => r.docstatus === 0).length) +
                " " +
                t("draft"),
            }),
          ]) +
          grid("g-2", [
            cols("Net Pay per Month", [
              {
                name: "Payroll",
                values: byMonth(
                  ss,
                  (r) => r.end_date,
                  (r) => r.net_pay,
                ),
              },
            ]),
            bars(
              "Net Pay by Department",
              group(
                cur,
                (r) => (EMP[r.employee] && EMP[r.employee].department) || r.department,
                (r) => r.net_pay,
              ),
              { money: true },
            ),
          ])
        );
      },
    },
    claims: {
      title: "Advances & Claims",
      load: async () => {
        const f = [
          "name",
          "employee",
          "posting_date",
          "total_claimed_amount",
          "total_sanctioned_amount",
          "total_amount_reimbursed",
          "approval_status",
          "status",
          "docstatus",
        ];
        const a = await getList("Expense Claim", f, [
          ["docstatus", "<", 2],
          ["posting_date", ">=", SINCE],
        ]);
        const b = await getList("Expense Claim", f, [
          ["docstatus", "<", 2],
          ["status", "in", ["Unpaid", "Draft"]],
        ]);
        const m = {};
        (a || []).concat(b || []).forEach((r) => (m[r.name] = r));
        return {
          adv: await getList(
            "Employee Advance",
            ["name", "employee", "posting_date", "advance_amount", "paid_amount", "claimed_amount", "return_amount", "status"],
            [["docstatus", "=", 1]],
          ),
          claims: a || b ? Object.values(m) : null,
          claimMap: m,
          det: await getList("Expense Claim Detail", ["parent", "expense_type", "amount"], [], { parent: "Expense Claim" }),
        };
      },
      render: (d) => {
        if (!d.adv && !d.claims) return na();
        const adv = (d.adv || [])
          .filter(passes)
          .map((r) => Object.assign({ out: (+r.paid_amount || 0) - (+r.claimed_amount || 0) - (+r.return_amount || 0) }, r));
        const cl = (d.claims || []).filter(passes);
        const pend = cl.filter((r) => r.docstatus === 0),
          unpaid = cl.filter((r) => r.docstatus === 1 && r.status === "Unpaid");
        const inp = cl.filter((r) => inP(r.posting_date));
        const det = (d.det || []).filter((x) => {
          const c = d.claimMap[x.parent];
          return c && passes(c) && inP(c.posting_date);
        });
        return (
          grid("g-kpi", [
            card("Outstanding Advances", money(sum(adv, (r) => Math.max(0, r.out))), {
              route: ["Employee Advance", { docstatus: 1, status: ["in", ["Paid", "Unpaid"]] }],
            }),
            card("Advances Awaiting Payment", num(adv.filter((r) => r.status === "Unpaid").length), {
              tone: "amber",
              route: ["Employee Advance", { status: "Unpaid" }],
            }),
            card("Claims Pending Approval", num(pend.length), { tone: "amber", route: ["Expense Claim", { docstatus: 0 }] }),
            card(
              "Unpaid Claims",
              money(sum(unpaid, (r) => (+r.total_sanctioned_amount || 0) - (+r.total_amount_reimbursed || 0))),
              { tone: "red", route: ["Expense Claim", { status: "Unpaid" }] },
            ),
            card("Claimed in Period", money(sum(inp, (r) => r.total_claimed_amount)), { tone: "gray" }),
          ]) +
          grid("g-2", [
            bars(
              "Claims by Type",
              group(
                det,
                (x) => x.expense_type,
                (x) => x.amount,
              ),
              { money: true },
            ),
            bars(
              "Outstanding Advances by Employee",
              group(
                adv.filter((r) => r.out > 0),
                (r) => ename(r.employee),
                (r) => r.out,
              ),
              { money: true, cls: "b3", limit: 8 },
            ),
          ])
        );
      },
    },
    recruit: {
      title: "Recruitment",
      load: async () => ({
        jo: await getList("Job Opening", ["name", "designation", "department", "company", "status"], [["status", "=", "Open"]]),
        app: await getList("Job Applicant", ["name", "status", "creation"], []),
        off: await getList("Job Offer", ["name", "status", "offer_date", "company"], [["docstatus", "<", 2]]),
        intv: await getList("Interview", ["name", "status", "scheduled_on"], [["docstatus", "<", 2]]),
      }),
      render: (d) => {
        if (!d.jo && !d.app && !d.off) return na();
        const byCo = (r) => !state.company || !r.company || r.company === state.company;
        const jo = (d.jo || []).filter((r) => byCo(r) && (!state.department || r.department === state.department));
        const app = d.app || [],
          off = (d.off || []).filter(byCo),
          intv = d.intv || [];
        const appP = app.filter((r) => inP(r.creation)),
          offP = off.filter((r) => inP(r.offer_date)),
          accP = offP.filter((r) => r.status === "Accepted");
        return (
          grid("g-kpi", [
            card("Open Positions", num(jo.length), { route: ["Job Opening", { status: "Open" }] }),
            card("Applicants", num(appP.length), { tone: "gray", route: ["Job Applicant", {}] }),
            card("Interviews Pending", num(intv.filter((r) => r.status === "Pending").length), {
              tone: "amber",
              route: ["Interview", { status: "Pending" }],
            }),
            card("Offers Awaiting Response", num(off.filter((r) => r.status === "Awaiting Response").length), {
              tone: "amber",
              route: ["Job Offer", { status: "Awaiting Response" }],
            }),
            card("Offers Accepted", num(accP.length), { tone: "green", route: ["Job Offer", { status: "Accepted" }] }),
          ]) +
          grid("g-2", [
            bars(
              "Hiring Funnel",
              [
                { label: "Applicants", value: appP.length },
                { label: "Interviews", value: intv.filter((r) => inP(r.scheduled_on)).length },
                { label: "Offers", value: offP.length },
                { label: "Accepted", value: accP.length },
              ],
              { cls: "b2" },
            ),
            bars(
              "Applicants by Status",
              group(app, (r) => r.status),
            ),
            bars(
              "Offers by Status",
              group(off, (r) => r.status),
              { cls: "b3" },
            ),
            bars(
              "Open Positions by Department",
              group(jo, (r) => r.department),
              { cls: "b2" },
            ),
          ])
        );
      },
    },
  };

  // ---------- Shell, events and start-up ----------
  const opt = (v, l, sel) => '<option value="' + esc(v) + '"' + (v === sel ? " selected" : "") + ">" + esc(l) + "</option>";
  const drawShell = () => {
    $("#hrd").setAttribute("dir", lang === "ar" ? "rtl" : "ltr");
    $("#title").textContent = t("HR Dashboard");
    $("#f-lang").textContent = lang === "ar" ? "English" : "العربية";
    const cos = [...new Set(EMPS.map((e) => e.company).filter(Boolean))].sort(),
      deps = [...new Set(EMPS.map((e) => e.department).filter(Boolean))].sort();
    $("#f-company").innerHTML = opt("", t("All Companies"), state.company) + cos.map((c) => opt(c, c, state.company)).join("");
    $("#f-dept").innerHTML =
      opt("", t("All Departments"), state.department) + deps.map((c) => opt(c, c, state.department)).join("");
    $("#f-period").innerHTML = PERIODS.map((p) => opt(p[0], t(p[1]), state.period)).join("");
    $("#tabs").innerHTML = Object.keys(SECTIONS)
      .map(
        (k) =>
          '<button type="button" class="hrd-tab' +
          (k === state.tab ? " on" : "") +
          '" data-tab="' +
          k +
          '">' +
          esc(t(SECTIONS[k].title)) +
          "</button>",
      )
      .join("");
  };
  const draw = async () => {
    const tab = state.tab,
      sec = SECTIONS[tab];
    if (!cache[tab]) {
      $("#body").innerHTML = '<div class="loading">' + esc(t("Loading...")) + "</div>";
      cache[tab] = await sec.load();
    }
    if (tab !== state.tab) return;
    let html;
    try {
      html = sec.render(cache[tab]);
    } catch (e) {
      console.error("HR Dashboard", e);
      html = na();
    }
    $("#body").innerHTML = html;
    $("#foot").textContent =
      t("Updated") +
      " " +
      new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }) +
      " · " +
      t("Figures follow your permissions");
  };
  const loadBase = async () => {
    const std = [
      "name",
      "employee_name",
      "status",
      "company",
      "department",
      "employment_type",
      "date_of_joining",
      "relieving_date",
      "contract_end_date",
    ];
    EMPS =
      (await getList("Employee", std.concat(["nationality", "sponsorship", "place_of_work", "custom_return_from_vacation"]))) ||
      (await getList("Employee", std)) ||
      [];
    EMPS.forEach((e) => {
      e.employee = e.name;
    });
    EMP = {};
    EMPS.forEach((e) => (EMP[e.name] = e));
  };

  $("#hrd").addEventListener("click", (ev) => {
    const tab = ev.target.closest("[data-tab]"),
      kpi = ev.target.closest("[data-route]");
    if (tab) {
      state.tab = tab.dataset.tab;
      drawShell();
      draw();
    } else if (kpi) {
      const r = JSON.parse(kpi.dataset.route);
      frappe.set_route("List", r[0], r[1]);
    } else if (ev.target.id === "f-lang") {
      lang = lang === "ar" ? "en" : "ar";
      drawShell();
      draw();
    } else if (ev.target.id === "f-refresh") {
      cache = {};
      loadBase().then(() => {
        drawShell();
        draw();
      });
    }
  });
  $("#hrd").addEventListener("change", (ev) => {
    if (ev.target.id === "f-company") state.company = ev.target.value;
    else if (ev.target.id === "f-dept") state.department = ev.target.value;
    else if (ev.target.id === "f-period") state.period = ev.target.value;
    else return;
    draw();
  });

  $("#body").innerHTML = '<div class="loading">' + esc(t("Loading...")) + "</div>";
  await loadBase();
  drawShell();
  draw();
})();
