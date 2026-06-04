import { useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
  ReferenceLine, RadarChart, PolarGrid, PolarAngleAxis, Radar,
  RadialBarChart, RadialBar,
} from "recharts";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8100";

/* ------------------------------------------------------------------ *
 *  ANNUAL REPORT ANALYST — institutional research terminal.
 *  Deep navy/slate ground, restrained institutional blue, a single
 *  gold accent. The register of S&P Global / BlackRock Aladdin /
 *  a buy-side research desk. Finance language throughout.
 *  Same figures and visuals as before — finance skin.
 * ------------------------------------------------------------------ */

const C = {
  bg: "#0B111B",          // deep navy-slate
  panel: "#111A28",
  panel2: "#16212F",
  edge: "#21303F",
  edgeSoft: "#1A2735",
  blue: "#4F8EF7",        // institutional blue
  blueDim: "#2C5798",
  gold: "#C9A24B",        // restrained gold accent
  green: "#3FAE7A",
  amber: "#D4972F",
  red: "#D75C4D",
  text: "#E4EAF2",
  textDim: "#8595A8",
  textFaint: "#566576",
};

function toNum(v) { return v == null || v === "" ? null : Number(v); }
function pct(v) { const n = toNum(v); return n == null || isNaN(n) ? "—" : `${(n * 100).toFixed(1)}%`; }
function mult(v) { const n = toNum(v); return n == null || isNaN(n) ? "—" : `${n.toFixed(2)}×`; }

const RATIO_LABELS = {
  gross_margin: "Gross margin", operating_margin: "Operating margin",
  net_margin: "Net margin", ebitda_margin: "EBITDA margin",
  current_ratio: "Current ratio", debt_to_equity: "Debt / equity",
  net_leverage: "Net leverage", return_on_equity: "Return on equity",
  return_on_assets: "Return on assets", interest_coverage: "Interest coverage",
  fcf_margin: "FCF margin",
};
const AS_PCT = new Set(["gross_margin","operating_margin","net_margin","ebitda_margin","return_on_equity","return_on_assets","fcf_margin"]);
const SECTORS = ["technology","healthcare","industrials","consumer","financials","energy","materials","other"];
const FIN_FIELDS = [
  ["revenue","Revenue"],["cost_of_revenue","Cost of revenue"],["operating_income","Operating income"],
  ["depreciation_amortization","D&A"],["interest_expense","Interest expense"],["net_income","Net income"],
  ["total_assets","Total assets"],["current_assets","Current assets"],["cash","Cash & equiv."],
  ["current_liabilities","Current liab."],["total_debt","Total debt"],["total_equity","Total equity"],
  ["operating_cash_flow","Operating CF"],["capex","Capex"],
];

export default function App() {
  const [memo, setMemo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [activeCite, setActiveCite] = useState(null);

  const [inputMode, setInputMode] = useState("text");
  const [company, setCompany] = useState("");
  const [sector, setSector] = useState("technology");
  const [fiscalYear, setFiscalYear] = useState("");
  const [filingText, setFilingText] = useState("");
  const [file, setFile] = useState(null);
  const [fin, setFin] = useState({});

  const setFinField = (k, v) => setFin((f) => ({ ...f, [k]: v }));
  function buildPayload() {
    const p = { company_name: company.trim() || "Unnamed Company", sector, fiscal_year: fiscalYear ? Number(fiscalYear) : null };
    for (const [k] of FIN_FIELDS) p[k] = toNum(fin[k]);
    return p;
  }
  async function call(url, options) {
    const res = await fetch(url, options);
    if (!res.ok) { const b = await res.text().catch(() => ""); throw new Error(`Server ${res.status}. ${b.slice(0,120)}`); }
    return res.json();
  }
  async function runSample() {
    setLoading(true); setError(""); setStatus("Analyzing…"); setActiveCite(null);
    try { setMemo(await call(`${API}/api/sample`)); setStatus(""); }
    catch (e) { setError(`${e.message} — is the backend running on ${API}?`); setStatus(""); }
    finally { setLoading(false); }
  }
  async function runAnalysis() {
    setLoading(true); setError(""); setStatus("Analyzing…"); setActiveCite(null);
    try {
      let d;
      if (inputMode === "pdf") {
        if (!file) throw new Error("Choose a PDF first, or switch to Text.");
        const fd = new FormData();
        fd.append("file", file); fd.append("statements_json", JSON.stringify(buildPayload()));
        d = await call(`${API}/api/analyze/pdf`, { method: "POST", body: fd });
      } else {
        d = await call(`${API}/api/analyze/text`, { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ statements: buildPayload(), filing_text: filingText }) });
      }
      setMemo(d); setStatus("");
    } catch (e) { setError(e.message); setStatus(""); }
    finally { setLoading(false); }
  }

  const ratioRows = memo && memo.ratios ? Object.entries(memo.ratios).filter(([, v]) => v != null) : [];
  const marginRows = ratioRows.filter(([k]) => AS_PCT.has(k));
  const health = memo?.health_score;
  const healthColor = health == null ? C.textDim : health >= 66 ? C.green : health >= 40 ? C.amber : C.red;
  const healthLabel = health == null ? "—" : health >= 66 ? "Strong" : health >= 40 ? "Adequate" : "Weak";

  const radarData = ratioRows
    .filter(([k]) => AS_PCT.has(k) || k === "current_ratio")
    .map(([k, v]) => ({
      axis: (RATIO_LABELS[k] || k).replace(" margin", "").replace("Return on ", "Ro"),
      val: AS_PCT.has(k) ? Math.max(0, Math.min(100, Number(v) * 100 * 2)) : Math.min(100, Number(v) * 33),
    }));

  const benchData = (memo?.benchmarks || []).map((b) => ({
    name: b.name.replace(" margin", "").replace("return on ", "Ro "),
    diff: Number((((b.value - b.norm) / Math.abs(b.norm || 1)) * 100).toFixed(0)),
    verdict: b.verdict,
  }));

  return (
    <div style={S.root}>
      <style>{GLOBAL}</style>

      {/* TOP BAR */}
      <div style={S.topbar}>
        <div style={S.brand}>
          <span style={S.brandMark}>▣</span>
          <span style={S.brandName}>ANNUAL REPORT ANALYST</span>
          <span style={S.brandSub}>EQUITY RESEARCH TERMINAL</span>
        </div>
        <div style={S.topRight}>
          <span style={S.statusChip}><span style={S.dot} />Live</span>
          <button style={S.sampleBtn} onClick={runSample} disabled={loading}>Load sample</button>
        </div>
      </div>

      <div style={S.body}>
        {/* LEFT — INPUTS */}
        <aside style={S.deck}>
          <div style={S.deckHead}>Company</div>
          <label style={S.lbl}>Company name</label>
          <input style={S.input} value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Acme Software Inc." />
          <div style={S.row}>
            <div style={{ flex: 1 }}>
              <label style={S.lbl}>Sector</label>
              <select style={S.input} value={sector} onChange={(e) => setSector(e.target.value)}>
                {SECTORS.map((s) => <option key={s} value={s} style={{ color: "#000" }}>{s}</option>)}
              </select>
            </div>
            <div style={{ width: 70 }}>
              <label style={S.lbl}>FY</label>
              <input style={S.input} value={fiscalYear} onChange={(e) => setFiscalYear(e.target.value)} placeholder="2024" />
            </div>
          </div>

          <div style={S.deckHead2}>Financials <span style={S.deckNote}>enter what you have</span></div>
          <div style={S.finGrid}>
            {FIN_FIELDS.map(([k, label]) => (
              <div key={k}>
                <label style={S.finLbl}>{label}</label>
                <input style={S.finInput} type="number" value={fin[k] ?? ""} onChange={(e) => setFinField(k, e.target.value)} placeholder="—" />
              </div>
            ))}
          </div>

          <div style={S.deckHead2}>Filing source</div>
          <div style={S.segmented}>
            <button onClick={() => setInputMode("text")} style={{ ...S.seg, ...(inputMode === "text" ? S.segOn : {}) }}>Paste text</button>
            <button onClick={() => setInputMode("pdf")} style={{ ...S.seg, ...(inputMode === "pdf" ? S.segOn : {}) }}>Upload PDF</button>
          </div>
          {inputMode === "text" ? (
            <textarea style={S.textarea} value={filingText} onChange={(e) => setFilingText(e.target.value)}
              placeholder="Paste filing narrative (MD&A, risk factors, business). Used to ground each claim in a cited passage." />
          ) : (
            <div style={S.fileBox}>
              <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} style={S.fileInput} />
              <p style={S.hint}>PDF parsed for grounding; figures from the form.</p>
            </div>
          )}

          <button style={S.runBtn} onClick={runAnalysis} disabled={loading}>
            {loading ? "Analyzing…" : "Run analysis"}
          </button>
          {status && <div style={S.statusLine}>{status}</div>}
          {error && <div style={S.error}>{error}</div>}
        </aside>

        {/* RIGHT — RESULTS */}
        <main style={S.main}>
          {!memo && !loading && !error && (
            <div style={S.empty}>
              <div style={S.emptyMark}>▣</div>
              <div style={S.emptyTitle}>No company loaded</div>
              <p style={S.emptyText}>
                Enter a company and its headline financials in the panel on the left,
                add the filing text or a PDF, and run the analysis. The terminal computes
                every ratio deterministically, benchmarks the sector, scores financial
                health, and grounds each claim in the source filing.
              </p>
            </div>
          )}

          {memo && (
            <>
              {/* HEADER */}
              <div style={S.targetHead}>
                <div>
                  <div style={S.targetTag}>EQUITY RESEARCH NOTE</div>
                  <div style={S.coName}>{memo.company_name || "—"}</div>
                  <div style={S.coMeta}>{(memo.sector || "—").toUpperCase()} &nbsp;·&nbsp; FY{memo.fiscal_year ?? "—"} &nbsp;·&nbsp; RESEARCH DRAFT</div>
                </div>
                <div style={S.targetStats}>
                  <Stat label="RATIOS" value={ratioRows.length} c={C.blue} />
                  <Stat label="STRENGTHS" value={memo.strengths?.length || 0} c={C.green} />
                  <Stat label="RISKS" value={memo.risks?.length || 0} c={(memo.risks?.length || 0) ? C.red : C.textDim} />
                  <Stat label="CITATIONS" value={memo.citations?.length || 0} c={C.gold} />
                </div>
              </div>

              {/* TOP ROW: gauge + radar + narrative */}
              <div style={S.topGrid}>
                <Panel title="FINANCIAL HEALTH">
                  <div style={S.gaugeWrap}>
                    <ResponsiveContainer width="100%" height={170}>
                      <RadialBarChart innerRadius="72%" outerRadius="100%" data={[{ v: health ?? 0, fill: healthColor }]}
                        startAngle={220} endAngle={-40}>
                        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                        <RadialBar background={{ fill: C.edge }} dataKey="v" cornerRadius={8} />
                      </RadialBarChart>
                    </ResponsiveContainer>
                    <div style={S.gaugeCenter}>
                      <div style={{ ...S.gaugeVal, color: healthColor }}>{health ?? "—"}</div>
                      <div style={{ ...S.gaugeLabel, color: healthColor }}>{healthLabel}</div>
                    </div>
                  </div>
                  <div style={S.gaugeNote}>Composite of sector-relative ratios, stress-adjusted.</div>
                </Panel>

                <Panel title="RATIO PROFILE">
                  {radarData.length >= 3 ? (
                    <ResponsiveContainer width="100%" height={210}>
                      <RadarChart data={radarData} outerRadius="72%">
                        <PolarGrid stroke={C.edge} />
                        <PolarAngleAxis dataKey="axis" tick={{ fill: C.textDim, fontSize: 9 }} />
                        <Radar dataKey="val" stroke={C.blue} fill={C.blue} fillOpacity={0.26} strokeWidth={1.5} />
                      </RadarChart>
                    </ResponsiveContainer>
                  ) : <p style={S.none}>Insufficient ratios for profile.</p>}
                </Panel>

                <Panel title="EXECUTIVE SUMMARY">
                  <div style={S.narrative}>{memo.narrative || "No summary generated."}</div>
                </Panel>
              </div>

              {/* MID ROW: ledger + margin bars */}
              <div style={S.midGrid}>
                <Panel title="FINANCIAL SUMMARY">
                  {ratioRows.length ? (
                    <table style={S.table}><tbody>
                      {ratioRows.map(([k, v]) => (
                        <tr key={k} style={S.tr}>
                          <td style={S.tdLabel}>{RATIO_LABELS[k] || k}</td>
                          <td style={S.tdVal}>{AS_PCT.has(k) ? pct(v) : mult(v)}</td>
                        </tr>
                      ))}
                    </tbody></table>
                  ) : <p style={S.none}>No ratios computable.</p>}
                </Panel>

                <Panel title="MARGIN PROFILE">
                  {marginRows.length ? (
                    <ResponsiveContainer width="100%" height={210}>
                      <BarChart data={marginRows.map(([k, v]) => ({ name: (RATIO_LABELS[k] || k).replace(" margin","").replace("Return on ","Ro"), value: Number((Number(v)*100).toFixed(1)) }))}
                        margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                        <CartesianGrid stroke={C.edge} vertical={false} />
                        <XAxis dataKey="name" stroke={C.textFaint} fontSize={9} angle={-18} textAnchor="end" height={50} />
                        <YAxis stroke={C.textFaint} fontSize={9} />
                        <Tooltip contentStyle={S.tooltip} formatter={(v) => [`${v}%`, ""]} cursor={{ fill: "rgba(79,142,247,0.07)" }} />
                        <ReferenceLine y={0} stroke={C.edge} />
                        <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                          {marginRows.map((_, i) => <Cell key={i} fill={C.blue} />)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <p style={S.none}>No margin data.</p>}
                </Panel>
              </div>

              {/* BENCHMARK DIVERGING */}
              {benchData.length > 0 && (
                <Panel title="SECTOR BENCHMARK" note="% above / below sector norm">
                  <ResponsiveContainer width="100%" height={Math.max(150, benchData.length * 34)}>
                    <BarChart data={benchData} layout="vertical" margin={{ left: 8, right: 30, top: 6, bottom: 6 }}>
                      <CartesianGrid stroke={C.edge} horizontal={false} />
                      <XAxis type="number" stroke={C.textFaint} fontSize={9} tickFormatter={(v) => `${v}%`} />
                      <YAxis type="category" dataKey="name" width={96} stroke={C.textDim} fontSize={10} />
                      <Tooltip contentStyle={S.tooltip} formatter={(v) => [`${v}% vs norm`, ""]} cursor={{ fill: "rgba(79,142,247,0.05)" }} />
                      <ReferenceLine x={0} stroke={C.textDim} />
                      <Bar dataKey="diff" radius={[0, 2, 2, 0]}>
                        {benchData.map((d, i) => <Cell key={i} fill={d.diff >= 0 ? C.green : C.red} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Panel>
              )}

              {/* SIGNALS + EVIDENCE */}
              <div style={S.midGrid}>
                <Panel title="STRENGTHS & RISKS">
                  <div style={S.sigLabel}>STRENGTHS</div>
                  {memo.strengths?.length ? (
                    <ul style={S.list}>{memo.strengths.map((s, i) => <li key={i} style={{ ...S.li, borderColor: C.green }}>{s}</li>)}</ul>
                  ) : <p style={S.none}>None flagged on available ratios.</p>}
                  <div style={{ ...S.sigLabel, marginTop: 14, color: C.red }}>RISKS</div>
                  {memo.risks?.length ? (
                    <ul style={S.list}>{memo.risks.map((s, i) => <li key={i} style={{ ...S.li, borderColor: C.red }}>{s}</li>)}</ul>
                  ) : <p style={S.none}>None flagged.</p>}
                </Panel>

                <Panel title="GROUNDED EVIDENCE" note="click a theme to view source">
                  {memo.citations?.length ? (
                    <>
                      <div style={S.cites}>
                        {memo.citations.map((c, i) => (
                          <button key={i} type="button" style={{ ...S.citeChip, ...(activeCite === i ? S.citeChipOn : {}) }}
                            onClick={() => setActiveCite(activeCite === i ? null : i)}>
                            <span style={S.citeTheme}>{(c.claim || "").replace(" (grounded)", "")}</span>
                            <span style={S.citeScore}>{Math.round((c.score || 0) * 100)}% {activeCite === i ? "▲" : "▼"}</span>
                          </button>
                        ))}
                      </div>
                      {activeCite != null && memo.citations[activeCite] ? (
                        <div style={S.passage}>
                          <div style={S.passageLabel}>
                            SOURCE · {(memo.citations[activeCite].claim || "").replace(" (grounded)", "").toUpperCase()}
                            {memo.citations[activeCite].page != null && <span> · p.{memo.citations[activeCite].page}</span>}
                          </div>
                          “{memo.citations[activeCite].source_text || "(no passage)"}”
                        </div>
                      ) : <div style={S.passageHint}>Click any theme to view the passage that grounds it.</div>}
                    </>
                  ) : <p style={S.none}>No filing supplied — add text or a PDF for grounded evidence.</p>}
                </Panel>
              </div>

              {memo.data_caveats?.length > 0 && (
                <div style={S.caveat}><span style={S.caveatTag}>DATA INTEGRITY</span> {memo.data_caveats.join(" ")}</div>
              )}
              <div style={S.foot}>Ratios computed deterministically · narrative grounded in source · decision-support, not a substitute for diligence</div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

function Stat({ label, value, c }) {
  return <div style={S.stat}><div style={{ ...S.statVal, color: c }}>{value}</div><div style={S.statLbl}>{label}</div></div>;
}
function Panel({ title, note, children }) {
  return (
    <section style={S.panel}>
      <div style={S.panelHead}>
        <span style={S.panelTitle}>{title}</span>
        {note && <span style={S.panelNote}>{note}</span>}
      </div>
      <div style={S.panelBody}>{children}</div>
    </section>
  );
}

const GLOBAL = `
  @import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&display=swap');
  * { box-sizing: border-box; margin: 0; }
  body { background: #0B111B; }
  ::-webkit-scrollbar { width: 10px; }
  ::-webkit-scrollbar-thumb { background: #21303F; border-radius: 5px; }
  ::-webkit-scrollbar-track { background: #0B111B; }
  input:focus, select:focus, textarea:focus { outline: none; border-color: #4F8EF7 !important; }
  input::placeholder, textarea::placeholder { color: #46566A; }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
`;

const S = {
  root: { minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "Archivo, sans-serif" },
  topbar: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 24px", height: 52, background: C.panel, borderBottom: `1px solid ${C.edge}` },
  brand: { display: "flex", alignItems: "center", gap: 12 },
  brandMark: { color: C.blue, fontSize: 15 },
  brandName: { fontFamily: "IBM Plex Mono, monospace", fontSize: 13, fontWeight: 600, letterSpacing: "0.14em", color: C.text },
  brandSub: { fontFamily: "IBM Plex Mono, monospace", fontSize: 9.5, letterSpacing: "0.2em", color: C.textFaint, borderLeft: `1px solid ${C.edge}`, paddingLeft: 12 },
  topRight: { display: "flex", alignItems: "center", gap: 12 },
  statusChip: { display: "flex", alignItems: "center", gap: 7, fontFamily: "IBM Plex Mono, monospace", fontSize: 10, letterSpacing: "0.12em", color: C.green },
  dot: { width: 7, height: 7, borderRadius: "50%", background: C.green, animation: "pulse 2s infinite" },
  sampleBtn: { padding: "7px 14px", background: "transparent", color: C.blue, border: `1px solid ${C.blueDim}`, borderRadius: 4, fontSize: 11.5, fontWeight: 600, fontFamily: "Archivo", cursor: "pointer" },

  body: { display: "grid", gridTemplateColumns: "310px 1fr", minHeight: "calc(100vh - 52px)" },
  deck: { background: C.panel, borderRight: `1px solid ${C.edge}`, padding: "20px 18px", overflowY: "auto" },
  deckHead: { fontFamily: "IBM Plex Mono, monospace", fontSize: 10.5, letterSpacing: "0.16em", color: C.gold, fontWeight: 600, marginBottom: 10, textTransform: "uppercase" },
  deckHead2: { fontFamily: "IBM Plex Mono, monospace", fontSize: 10.5, letterSpacing: "0.16em", color: C.gold, fontWeight: 600, margin: "20px 0 10px", paddingTop: 14, borderTop: `1px solid ${C.edgeSoft}`, textTransform: "uppercase" },
  deckNote: { color: C.textFaint, fontWeight: 400, letterSpacing: 0, textTransform: "none" },
  lbl: { display: "block", fontSize: 10.5, color: C.textDim, marginBottom: 5, marginTop: 10 },
  input: { width: "100%", background: C.bg, border: `1px solid ${C.edge}`, borderRadius: 4, padding: "8px 10px", color: C.text, fontSize: 13, fontFamily: "Archivo" },
  row: { display: "flex", gap: 10 },
  finGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 },
  finLbl: { display: "block", fontSize: 9.5, color: C.textFaint, marginBottom: 3, marginTop: 5 },
  finInput: { width: "100%", background: C.bg, border: `1px solid ${C.edge}`, borderRadius: 4, padding: "6px 8px", color: C.text, fontSize: 12, fontFamily: "IBM Plex Mono, monospace" },
  segmented: { display: "flex", border: `1px solid ${C.edge}`, borderRadius: 5, overflow: "hidden" },
  seg: { flex: 1, padding: "8px", background: "transparent", color: C.textDim, border: "none", fontSize: 12, fontFamily: "Archivo", cursor: "pointer" },
  segOn: { background: C.blue, color: "#fff", fontWeight: 600 },
  textarea: { width: "100%", minHeight: 100, background: C.bg, border: `1px solid ${C.edge}`, borderRadius: 4, padding: "10px", color: C.text, fontSize: 12.5, fontFamily: "Archivo", lineHeight: 1.5, resize: "vertical", marginTop: 10 },
  fileBox: { padding: 14, background: C.bg, border: `1px dashed ${C.edge}`, borderRadius: 4, marginTop: 10 },
  fileInput: { fontSize: 12, color: C.textDim, width: "100%" },
  hint: { fontSize: 10.5, color: C.textFaint, marginTop: 8, lineHeight: 1.4 },
  runBtn: { width: "100%", marginTop: 18, padding: "12px", background: C.blue, color: "#fff", border: "none", borderRadius: 5, fontSize: 13, fontWeight: 700, fontFamily: "Archivo", cursor: "pointer", letterSpacing: "0.03em" },
  statusLine: { marginTop: 10, fontSize: 11.5, color: C.blue, fontFamily: "IBM Plex Mono, monospace", textAlign: "center" },
  error: { marginTop: 12, background: "rgba(215,92,77,0.1)", color: C.red, padding: "10px 12px", borderRadius: 4, fontSize: 12, border: `1px solid ${C.red}`, lineHeight: 1.45 },

  main: { padding: "20px 24px", overflowY: "auto" },
  empty: { textAlign: "center", padding: "90px 20px" },
  emptyMark: { fontSize: 32, color: C.blueDim, marginBottom: 18 },
  emptyTitle: { fontFamily: "IBM Plex Mono, monospace", fontSize: 13, letterSpacing: "0.16em", color: C.textDim, marginBottom: 12 },
  emptyText: { maxWidth: 450, margin: "0 auto", fontSize: 13.5, lineHeight: 1.7, color: C.textFaint },

  targetHead: { display: "flex", justifyContent: "space-between", alignItems: "center", background: C.panel, border: `1px solid ${C.edge}`, borderRadius: 8, padding: "16px 20px", marginBottom: 14, borderLeft: `3px solid ${C.gold}` },
  targetTag: { fontFamily: "IBM Plex Mono, monospace", fontSize: 9.5, letterSpacing: "0.2em", color: C.gold },
  coName: { fontFamily: "Newsreader, serif", fontSize: 27, fontWeight: 500, color: C.text, lineHeight: 1.05, margin: "7px 0 5px" },
  coMeta: { fontFamily: "IBM Plex Mono, monospace", fontSize: 10.5, color: C.textFaint, letterSpacing: "0.08em" },
  targetStats: { display: "flex", gap: 24 },
  stat: { textAlign: "center" },
  statVal: { fontFamily: "Newsreader, serif", fontSize: 28, fontWeight: 500, lineHeight: 1 },
  statLbl: { fontFamily: "IBM Plex Mono, monospace", fontSize: 8.5, letterSpacing: "0.14em", color: C.textFaint, marginTop: 5 },

  topGrid: { display: "grid", gridTemplateColumns: "260px 280px 1fr", gap: 14, marginBottom: 14 },
  midGrid: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 14 },

  panel: { background: C.panel, border: `1px solid ${C.edge}`, borderRadius: 8 },
  panelHead: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 14px", borderBottom: `1px solid ${C.edge}`, background: C.panel2, borderRadius: "8px 8px 0 0" },
  panelTitle: { fontFamily: "IBM Plex Mono, monospace", fontSize: 10.5, letterSpacing: "0.14em", color: C.gold, fontWeight: 600 },
  panelNote: { fontFamily: "IBM Plex Mono, monospace", fontSize: 9, color: C.textFaint },
  panelBody: { padding: "14px 16px" },

  gaugeWrap: { position: "relative" },
  gaugeCenter: { position: "absolute", top: "52%", left: 0, right: 0, textAlign: "center", transform: "translateY(-50%)" },
  gaugeVal: { fontFamily: "Newsreader, serif", fontSize: 42, fontWeight: 600, lineHeight: 1 },
  gaugeLabel: { fontFamily: "IBM Plex Mono, monospace", fontSize: 10, letterSpacing: "0.14em", marginTop: 2 },
  gaugeNote: { fontSize: 10, color: C.textFaint, textAlign: "center", marginTop: 6, lineHeight: 1.4 },

  narrative: { fontFamily: "Newsreader, serif", fontSize: 15.5, lineHeight: 1.64, color: C.text },
  table: { width: "100%", borderCollapse: "collapse" },
  tr: { borderBottom: `1px solid ${C.edgeSoft}` },
  tdLabel: { padding: "6px 0", fontSize: 12.5, color: C.textDim },
  tdVal: { padding: "6px 0", fontSize: 13, fontFamily: "IBM Plex Mono, monospace", fontWeight: 600, textAlign: "right", color: C.text },
  sigLabel: { fontFamily: "IBM Plex Mono, monospace", fontSize: 9.5, letterSpacing: "0.14em", color: C.green, marginBottom: 8 },
  list: { listStyle: "none", display: "flex", flexDirection: "column", gap: 6, padding: 0 },
  li: { fontSize: 12.5, lineHeight: 1.42, color: C.text, borderLeft: "3px solid", background: C.panel2, padding: "8px 11px", borderRadius: "0 3px 3px 0" },
  none: { fontSize: 12.5, color: C.textFaint, fontStyle: "italic" },
  cites: { display: "flex", flexWrap: "wrap", gap: 8 },
  citeChip: { display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 2, background: C.panel2, border: `1px solid ${C.blueDim}`, borderRadius: 4, padding: "8px 13px", cursor: "pointer", fontFamily: "Archivo", textAlign: "left" },
  citeChipOn: { borderColor: C.blue, background: "#172A45", boxShadow: `0 0 0 1px ${C.blue}` },
  citeTheme: { fontSize: 12, fontWeight: 600, color: C.text, textTransform: "capitalize" },
  citeScore: { fontSize: 9.5, fontFamily: "IBM Plex Mono, monospace", color: C.blue },
  passage: { marginTop: 11, background: C.bg, borderLeft: `3px solid ${C.gold}`, padding: "12px 15px", borderRadius: "0 4px 4px 0", fontFamily: "Newsreader, serif", fontSize: 14, lineHeight: 1.58, fontStyle: "italic", color: C.text },
  passageLabel: { fontFamily: "IBM Plex Mono, monospace", fontSize: 9, letterSpacing: "0.12em", color: C.gold, marginBottom: 7, fontStyle: "normal" },
  passageHint: { marginTop: 11, fontSize: 11.5, color: C.textFaint, fontStyle: "italic" },
  caveat: { background: C.panel, border: `1px solid ${C.edge}`, borderLeft: `3px solid ${C.gold}`, borderRadius: 4, padding: "11px 14px", fontSize: 12, color: C.textDim, lineHeight: 1.5, marginBottom: 14 },
  caveatTag: { fontFamily: "IBM Plex Mono, monospace", fontSize: 9, letterSpacing: "0.12em", color: C.gold, marginRight: 8 },
  foot: { padding: "14px 0", fontFamily: "IBM Plex Mono, monospace", fontSize: 9, letterSpacing: "0.06em", color: C.textFaint, textAlign: "center", borderTop: `1px solid ${C.edge}` },
  tooltip: { background: C.panel2, border: `1px solid ${C.edge}`, borderRadius: 4, color: C.text, fontSize: 11 },
};
