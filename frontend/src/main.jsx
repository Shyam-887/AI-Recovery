import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import "./case.css";
const API = import.meta.env.VITE_API_URL || "/api/v1";
async function api(path, opt = {}) {
  const h = {
    ...(opt.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(opt.headers || {}),
  };
  const t = localStorage.getItem("token");
  if (t) h.Authorization = `Bearer ${t}`;
  let r;
  try {
    r = await fetch(API + path, { ...opt, headers: h });
  } catch (error) {
    throw Error(`Backend connection failed at ${API}. Start the backend and try again.`);
  }
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401) {
      localStorage.removeItem("token");
      throw Error("Your session expired. Please sign in again.");
    }
    throw Error(d.detail || `Request failed (${r.status})`);
  }
  return d;
}
function Login({ done }) {
  const [reg, setReg] = useState(false),
    [f, setF] = useState({ organization_name: "", email: "", password: "" }),
    [e, setE] = useState("");
  async function submit(x) {
    x.preventDefault();
    setE("");
    try {
      const d = await api(reg ? "/auth/register" : "/auth/login", {
        method: "POST",
        body: JSON.stringify(f),
      });
      localStorage.setItem("token", d.access_token);
      done();
    } catch (x) {
      setE(x.message);
    }
  }
  return (
    <div className="auth">
      <div className="card auth-card">
        <div className="brand-mark">AR</div>
        <b>AI Revenue Recovery</b>
        <h1>{reg ? "Create workspace" : "Welcome back"}</h1>
        <p>Revenue intelligence and automated payment recovery.</p>
        <form onSubmit={submit}>
          {reg && (
            <input
              required
              placeholder="Organization name"
              value={f.organization_name}
              onChange={(x) =>
                setF({ ...f, organization_name: x.target.value })
              }
            />
          )}
          <input
            required
            type="email"
            placeholder="Email"
            value={f.email}
            onChange={(x) => setF({ ...f, email: x.target.value })}
          />
          <input
            required
            minLength="8"
            type="password"
            placeholder="Password"
            value={f.password}
            onChange={(x) => setF({ ...f, password: x.target.value })}
          />
          {e && <div className="err">{e}</div>}
          <button>{reg ? "Create account" : "Sign in"}</button>
        </form>
        <a onClick={() => setReg(!reg)}>
          {reg ? "Already have an account? Sign in" : "Create a new account"}
        </a>
      </div>
    </div>
  );
}
function Method({ value, provider }) {
  const v = (value || "card").toLowerCase();
  const label = v.replace(/\s*•+.*/, "");
  return (
    <div className="method">
      <span className="method-icon">
        {label.includes("upi") ? "U" : label.includes("bank") ? "B" : "▣"}
      </span>
      <span>
        <strong>{label.toUpperCase()}</strong>
        <small>
          {value?.includes("••••") ? value : provider || "secure payment"}
        </small>
      </span>
    </div>
  );
}
function Status({ value }) {
  return (
    <span
      className={`status ${String(value || "")
        .toLowerCase()
        .replaceAll("_", "-")}`}
    >
      {String(value || "unknown").replaceAll("_", " ")}
    </span>
  );
}
function App() {
  const [ok, setOk] = useState(!!localStorage.getItem("token"));
  const [darkMode, setDarkMode] = useState(localStorage.getItem("theme") === "dark");
  const [cases, setCases] = useState([]),
    [payments, setPayments] = useState([]),
    [err, setErr] = useState(""),
    [refreshing, setRefreshing] = useState(false),
    [query, setQuery] = useState(""),
    [searchQuery, setSearchQuery] = useState(""),
    [status, setStatus] = useState("all"),
    [uploading, setUploading] = useState(null),
    [openCase, setOpenCase] = useState(null),
    [selectedStat, setSelectedStat] = useState(null),
    [showPaymentForm, setShowPaymentForm] = useState(false),
    [paymentForm, setPaymentForm] = useState({
      customer_name: "",
      customer_email: "",
      amount: "",
      currency: "INR",
      status: "success",
      payment_method: "card",
      provider: "manual",
      payment_number: "",
    });
  async function load() {
    if (refreshing) return;
    setRefreshing(true);
    try {
      const [c, p] = await Promise.all([
        api("/recovery/cases"),
        api("/payments"),
      ]);
      setCases(c);
      setPayments(p);
      setErr("");
    } catch (e) {
      setErr(e.message);
      if (!localStorage.getItem("token")) setOk(false);
    } finally {
      setRefreshing(false);
    }
  }
  useEffect(() => {
    if (ok) load();
  }, [ok]);
  async function uploadReceipt(paymentId, event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const body = new FormData();
    body.append("receipt", file);
    setUploading(paymentId);
    try {
      const result = await api(`/payments/${paymentId}/receipt`, {
        method: "POST",
        body,
      });
      setPayments((current) =>
        current.map((payment) =>
          payment.id === paymentId
            ? { ...payment, receipt_filename: result.receipt_filename }
            : payment,
        ),
      );
      setErr("");
    } catch (e) {
      setErr(e.message);
    } finally {
      setUploading(null);
      event.target.value = "";
    }
  }
  async function createPayment(event) {
    event.preventDefault();
    try {
      await api("/payments", {
        method: "POST",
        body: JSON.stringify({
          ...paymentForm,
          amount: Number(paymentForm.amount),
          customer_email: paymentForm.customer_email || null,
          provider: paymentForm.provider || null,
          payment_number: paymentForm.payment_number || null,
        }),
      });
      setPaymentForm({
        customer_name: "",
        customer_email: "",
        amount: "",
        currency: "INR",
        status: "success",
        payment_method: "card",
        provider: "manual",
        payment_number: "",
      });
      setShowPaymentForm(false);
      setSearchQuery("");
      setQuery("");
      setStatus("all");
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }
  function clearPaymentForm() {
    setPaymentForm({
      customer_name: "",
      customer_email: "",
      amount: "",
      currency: "INR",
      status: "success",
      payment_method: "card",
      provider: "manual",
      payment_number: "",
    });
  }
  function openStat(stat, target) {
    setSelectedStat(stat);
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  async function tryRecovery(caseId) {
    try {
      await api(`/recovery/cases/${caseId}/execute`, { method: "POST" });
      setErr("");
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }
  async function markRecovered(caseId) {
    try {
      await api(`/recovery/cases/${caseId}/mark-recovered`, { method: "POST" });
      setErr("");
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }
  async function clearPayment(paymentId) {
    if (!window.confirm("Clear this payment record?")) return;
    try {
      await api(`/payments/${paymentId}`, { method: "DELETE" });
      setErr("");
      await load();
    } catch (e) {
      setErr(e.message);
    }
  }
  useEffect(() => {
    document.body.classList.toggle("dark-mode", darkMode);
    localStorage.setItem("theme", darkMode ? "dark" : "light");
  }, [darkMode]);
  const filtered = useMemo(
    () =>
      payments.filter((p) => {
        const q = searchQuery.toLowerCase();
        const hit =
          !q ||
          [p.customer, p.transaction_id, p.payment_method, p.provider]
            .join(" ")
            .toLowerCase()
            .includes(q);
        return hit && (status === "all" || p.status === status);
      }),
    [payments, searchQuery, status],
  );
  if (!ok) return <Login done={() => setOk(true)} />;
  const total = payments.reduce((a, p) => a + Number(p.amount || 0), 0),
    successful = payments.filter((p) =>
      ["succeeded", "success", "paid", "recovered"].includes(
        String(p.status).toLowerCase(),
      ),
    ).length,
    failed = payments.filter((p) =>
      String(p.status).toLowerCase().includes("fail"),
    ).length;
  const selectedPayment = filtered.length === 1 ? filtered[0] : null;
  const caseStatuses = [
    { key: "queued", label: "Queued" },
    { key: "approval_required", label: "Approval required" },
    { key: "action_ready", label: "Action ready" },
    { key: "action_executed", label: "Action executed" },
    { key: "recovered", label: "Recovered" },
  ].map((item) => ({
    ...item,
    count: cases.filter((itemCase) => itemCase.status === item.key).length,
  }));
  const totalCases = cases.length || 1;
  const visibleCases = selectedStat === "cases"
    ? cases
    : selectedStat === "approval_required"
      ? cases.filter((itemCase) => itemCase.status === "approval_required")
      : selectedStat === "action_ready"
        ? cases.filter((itemCase) => itemCase.status === "action_ready")
        : selectedStat === "action_executed"
          ? cases.filter((itemCase) => itemCase.status === "action_executed")
        : selectedStat === "recovered"
          ? cases.filter((itemCase) => itemCase.status === "recovered")
          : cases;
  return (
    <div className="app-shell">
      <header>
        <div className="header-brand">
          <div className="brand-mark small">AR</div>
          <div>
            <b>AI Revenue Recovery</b>
            <small>Payment command center</small>
          </div>
        </div>
        <div className="header-actions">
          <button
            type="button"
            className="secondary theme-toggle"
            aria-pressed={darkMode}
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? "Light mode" : "Dark mode"}
          </button>
          <button
            className="secondary"
            onClick={() => {
              localStorage.removeItem("token");
              setOk(false);
            }}
          >
            Sign out
          </button>
        </div>
      </header>
      <main>
        <section className="hero">
          <div>
            <small className="eyebrow">PAYMENT INTELLIGENCE</small>
            <h1>Recover more revenue with a clearer payment picture.</h1>
            <p>
              Track every payment, method and recovery signal from one
              workspace.
            </p>
          </div>
          <div>
            <button onClick={() => setShowPaymentForm(!showPaymentForm)}>
              {showPaymentForm ? "Close" : "Record payment"}
            </button>
            <button
              type="button"
              className="secondary refresh-button"
              onClick={load}
              disabled={refreshing}
            >
              {refreshing ? "Refreshing..." : "↻ Refresh"}
            </button>
          </div>
        </section>
        {err && <div className="err">{err}</div>}
        {showPaymentForm && (
          <form className="panel" onSubmit={createPayment}>
            <small className="eyebrow">NEW PAYMENT</small>
            <h2>Record a payment</h2>
            <div className="filters payment-fields">
              <input
                required
                placeholder="Customer name"
                value={paymentForm.customer_name}
                onChange={(e) =>
                  setPaymentForm({ ...paymentForm, customer_name: e.target.value })
                }
              />
              <input
                type="email"
                placeholder="Customer email"
                value={paymentForm.customer_email}
                onChange={(e) =>
                  setPaymentForm({ ...paymentForm, customer_email: e.target.value })
                }
              />
              <input
                required
                min="0.01"
                step="0.01"
                type="number"
                placeholder="Amount"
                value={paymentForm.amount}
                onChange={(e) => setPaymentForm({ ...paymentForm, amount: e.target.value })}
              />
              <input
                placeholder="Payment number"
                value={paymentForm.payment_number}
                onChange={(e) =>
                  setPaymentForm({ ...paymentForm, payment_number: e.target.value })
                }
              />
              <select
                value={paymentForm.status}
                onChange={(e) => setPaymentForm({ ...paymentForm, status: e.target.value })}
              >
                <option value="success">Success</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
              </select>
              <select
                value={paymentForm.payment_method}
                onChange={(e) =>
                  setPaymentForm({ ...paymentForm, payment_method: e.target.value })
                }
              >
                <option value="card">Card</option>
                <option value="upi">UPI</option>
                <option value="bank_transfer">Bank transfer</option>
              </select>
            </div>
            <div className="form-actions">
              <button type="submit">Payment</button>
              <button type="button" className="secondary" onClick={clearPaymentForm}>
                Clear
              </button>
            </div>
          </form>
        )}
        <section className="stats">
          <button className={`stat-card ${selectedStat === "total" ? "selected" : ""}`} onClick={() => openStat("total", "payment-history")}>
            <span>Total payment volume</span>
            <strong>₹{total.toLocaleString()}</strong>
            <small>{payments.length} recorded payments</small>
          </button>
          <button className={`stat-card ${selectedStat === "successful" ? "selected" : ""}`} onClick={() => openStat("successful", "payment-history")}>
            <span>Successful</span>
            <strong>{successful}</strong>
            <small>Completed or recovered</small>
          </button>
          <button className={`stat-card ${selectedStat === "failed" ? "selected" : ""}`} onClick={() => openStat("failed", "payment-history")}>
            <span>Failed</span>
            <strong>{failed}</strong>
            <small>Needs recovery attention</small>
          </button>
          <button className={`stat-card ${selectedStat === "cases" ? "selected" : ""}`} onClick={() => openStat("cases", "recovery-queue")}>
            <span>Open recovery cases</span>
            <strong>{cases.length}</strong>
            <small>AI workflow queue</small>
          </button>
        </section>
        <section className="panel recovery-chart-panel">
          <div className="panel-head">
            <div>
              <small className="eyebrow">RECOVERY OVERVIEW</small>
              <h2>Recovery cases</h2>
              <p>{cases.length} total cases received</p>
            </div>
          </div>
          <div className="recovery-chart" aria-label="Recovery cases by status">
            {caseStatuses.map((item) => (
              <button
                type="button"
                className={`chart-row ${selectedStat === item.key ? "selected" : ""}`}
                key={item.key}
                onClick={() => setSelectedStat(item.key)}
              >
                <div className="chart-label">
                  <span className={`chart-dot ${item.key}`} />
                  <strong>{item.label}</strong>
                  <span>{item.count} case{item.count === 1 ? "" : "s"}</span>
                </div>
                <div className="chart-track">
                  <div
                    className={`chart-bar ${item.key}`}
                    style={{ width: `${(item.count / totalCases) * 100}%` }}
                  />
                </div>
                <strong className="chart-percent">
                  {Math.round((item.count / totalCases) * 100)}%
                </strong>
              </button>
            ))}
          </div>
        </section>
        <section className="panel" id="payment-history">
          <div className="panel-head">
            <div>
              <small className="eyebrow">TRANSACTION LEDGER</small>
              <h2>Payment history</h2>
              <p>
                Recent payment attempts with method, status and provider
                details.
              </p>
            </div>
            <div className="filters">
              <input
                aria-label="Payment number"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter payment number to search"
              />
              <button
                type="button"
                onClick={() => {
                  setSearchQuery(query);
                }}
              >
                Search
              </button>
              <label
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  cursor: "pointer",
                  fontWeight: 700,
                  color: "#172033",
                  whiteSpace: "nowrap",
                }}
              >
                Add payment file
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png,.webp"
                  disabled={!selectedPayment}
                  onChange={(e) => {
                    if (selectedPayment) uploadReceipt(selectedPayment.id, e);
                    else setErr("Search one payment before adding a file.");
                  }}
                  style={{ display: "none" }}
                />
              </label>
              <select
                aria-label="Payment status"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="all">All statuses</option>
                <option value="failed">Failed</option>
                <option value="success">Success</option>
                <option value="succeeded">Succeeded</option>
                <option value="pending">Pending</option>
                <option value="processing">Processing</option>
              </select>
            </div>
          </div>
          {searchQuery && (
            <div className="search-result">
              {filtered.length ? (
                <>
                  <strong>{filtered.length} payment found.</strong>
                  {filtered.length === 1 && (
                    <>
                      <span> Status: </span>
                      <Status value={filtered[0].status} />
                    </>
                  )}
                </>
              ) : (
                <>
                  Payment <strong>{searchQuery}</strong> was not found.
                </>
              )}
            </div>
          )}
          {filtered.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Transaction</th>
                    <th>Customer</th>
                    <th>Payment method</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Payment file</th>
                    <th>Date</th>
                    <th>Clear</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <strong className="mono">{p.transaction_id}</strong>
                        <small>
                          {p.provider || "Internal"} · Attempt{" "}
                          {p.attempt_number}
                        </small>
                      </td>
                      <td>
                        <strong>{p.customer}</strong>
                        <small>{p.customer_id.slice(0, 8)}…</small>
                      </td>
                      <td>
                        <Method
                          value={p.payment_method}
                          provider={p.provider}
                        />
                      </td>
                      <td>
                        <strong>₹{Number(p.amount).toLocaleString()}</strong>
                        <small>{p.currency}</small>
                      </td>
                      <td>
                        <Status value={p.status} />
                        {p.failure_reason && (
                          <small className="reason">{p.failure_reason}</small>
                        )}
                      </td>
                      <td>
                        <label
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            cursor: "pointer",
                            fontWeight: 700,
                            color: "#172033",
                          }}
                        >
                          <span>
                            {uploading === p.id
                              ? "Uploading..."
                              : p.receipt_filename
                                ? "Replace file"
                                : "Add payment file"}
                          </span>
                          <input
                            type="file"
                            accept=".pdf,.jpg,.jpeg,.png,.webp"
                            onChange={(e) => uploadReceipt(p.id, e)}
                            disabled={uploading === p.id}
                            style={{ display: "none" }}
                          />
                        </label>
                        {p.receipt_filename && <small>{p.receipt_filename}</small>}
                      </td>
                      <td>
                        <strong>
                          {p.created_at
                            ? new Date(p.created_at).toLocaleDateString("en-IN")
                            : "—"}
                        </strong>
                        <small>
                          {p.created_at
                            ? new Date(p.created_at).toLocaleTimeString(
                                "en-IN",
                                { hour: "2-digit", minute: "2-digit" },
                              )
                            : ""}
                        </small>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="clear-payment-button"
                          onClick={() => clearPayment(p.id)}
                        >
                          Clear payment
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty">No payments match your filters.</p>
          )}
        </section>
        <section className="panel" id="recovery-queue">
          <div className="panel-head">
            <div>
              <small className="eyebrow">RECOVERY QUEUE</small>
              <h2>Recovery cases</h2>
              <p>
                AI decisions and actions connected to failed payments.
                {selectedStat && selectedStat !== "total" && selectedStat !== "successful" && selectedStat !== "failed" ? ` Showing ${selectedStat.replaceAll("_", " ")} cases.` : ""}
              </p>
            </div>
          </div>
          {cases.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>Amount</th>
                    <th>Payment through</th>
                    <th>Risk</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleCases.map((c) => (
                    <React.Fragment key={c.case_id}>
                      <tr>
                      <td>
                        <strong>{c.customer_name || c.customer_id}</strong>
                      </td>
                      <td>
                        ₹{Number(c.amount || 0).toLocaleString()}{" "}
                        <small>{c.currency}</small>
                      </td>
                      <td>
                        <strong>{c.payment_method || "Unknown"}</strong>
                        <small>{c.provider || "Manual"}</small>
                      </td>
                      <td>
                        <span className="risk">{c.risk_score ?? "—"}</span>
                      </td>
                      <td>
                        <Status value={c.status} />
                      </td>
                      <td>
                        <button
                          type="button"
                          className="case-open-button"
                          onClick={() => setOpenCase(openCase?.case_id === c.case_id ? null : c)}
                        >
                          {openCase?.case_id === c.case_id ? "Close case" : "Open case"}
                        </button>
                        {c.status === "approval_required" || c.status === "action_ready" ? (
                          <button
                            type="button"
                            className="case-retry-button"
                            onClick={() => tryRecovery(c.case_id)}
                          >
                            Try recovery
                          </button>
                        ) : null}
                        {c.status === "action_executed" ? (
                          <button
                            type="button"
                            className="case-recovered-button"
                            onClick={() => markRecovered(c.case_id)}
                          >
                            Mark recovered
                          </button>
                        ) : null}
                      </td>
                      </tr>
                      {openCase?.case_id === c.case_id && (
                      <tr className="case-detail-row">
                          <td colSpan="6">
                          <div className="case-detail">
                            <div>
                              <small>CASE ID</small>
                              <strong className="mono">{c.case_id}</strong>
                            </div>
                            <div>
                              <small>REASON</small>
                              <strong>{c.reason || "Payment failed"}</strong>
                            </div>
                            <div>
                              <small>RECOVERY STATUS</small>
                              <Status value={c.status} />
                            </div>
                            <div>
                              <small>PAYMENT STATUS</small>
                              <Status value={c.payment_status || "unknown"} />
                            </div>
                            <div>
                              <small>RECOVERY ACTION</small>
                              <strong>{c.action || "Pending AI decision"}</strong>
                            </div>
                            <div className="case-solution">
                              <small>RECOMMENDED SOLUTION</small>
                              <strong>{c.action_message || "AI is analyzing this case. Refresh after processing."}</strong>
                            </div>
                            <div>
                              <small>AI ROOT CAUSE</small>
                              <strong>{c.root_cause || "Pending analysis"}</strong>
                            </div>
                            <div>
                              <small>AI CONFIDENCE</small>
                              <strong>{c.confidence != null ? `${Math.round(c.confidence * 100)}%` : "Pending analysis"}</strong>
                            </div>
                            <div>
                              <small>RECOVERY PROBABILITY</small>
                              <strong>{c.recovery_probability != null ? `${Math.round(c.recovery_probability * 100)}%` : "Pending analysis"}</strong>
                            </div>
                            <div>
                              <small>APPROVAL</small>
                              <strong>{c.human_approval_required ? "Required" : "Not required"}</strong>
                            </div>
                          </div>
                        </td>
                      </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="empty">No recovery cases yet.</p>
          )}
        </section>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")).render(<App />);
