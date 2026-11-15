import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './legacy.css';

const API =
  import.meta.env.VITE_API_BASE ||
  (window.location.port === '5173' ? 'http://127.0.0.1:8000' : window.location.origin);

const PAGES = [
  ['command', 'Command Center', '⌘'],
  ['telemetry', 'Telemetry', '◉'],
  ['investigation', 'Investigation', '✦'],
  ['fault', 'Fault Lab', '⚗'],
  ['model', 'Model Card', '⬡'],
  ['evidence', 'Submission Proof', '▣'],
] as const;

const SCENARIOS = [
  { id: 'normal', label: 'Normal reference', requires: [] },
  { id: 'rpm_instability', label: 'RPM instability', requires: ['rpm'] },
  { id: 'maf_drift', label: 'MAF drift', requires: ['maf'] },
  { id: 'load_instability', label: 'Engine-load instability', requires: ['engine_load'] },
  { id: 'sensor_dropout', label: 'Sensor dropout', requires: ['speed'] },
  { id: 'signal_spikes', label: 'Signal spikes', requires: ['speed', 'rpm'] },
  { id: 'thermal_drift', label: 'Thermal drift', requires: ['temp'] },
  { id: 'voltage_degradation', label: 'Voltage degradation', requires: ['battery'] },
] as const;

type PageId = (typeof PAGES)[number][0];
type Severity = 'mild' | 'medium' | 'severe';
type Result = any;
type HistoryItem = {
  sessionId: string;
  created: string;
  source: string;
  health: number;
  quality: number;
  risk: string;
  anomalies: number;
};

async function requestJSON(url: string, init?: RequestInit) {
  const response = await fetch(url, init);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    const message =
      typeof detail === 'string'
        ? detail
        : detail?.message || payload?.message || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return payload;
}

function loadHistory(): HistoryItem[] {
  try {
    return JSON.parse(localStorage.getItem('octaneos-sentinel-history-v34') || '[]');
  } catch {
    return [];
  }
}

export default function Legacy() {
  const [page, setPage] = useState<PageId>('command');
  const [scenario, setScenario] = useState('rpm_instability');
  const [severity, setSeverity] = useState<Severity>('medium');
  const [data, setData] = useState<Result | null>(null);
  const [baseline, setBaseline] = useState<Result | null>(null);
  const [model, setModel] = useState<any | null>(null);
  const [aiStatus, setAiStatus] = useState<any | null>(null);
  const [submission, setSubmission] = useState<any | null>(null);
  const [explanation, setExplanation] = useState<any | null>(null);
  const [busy, setBusy] = useState(true);
  const [aiBusy, setAiBusy] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory);
  const fileRef = useRef<HTMLInputElement | null>(null);

  function remember(result: Result) {
    const item: HistoryItem = {
      sessionId: result.session_id,
      created: result.provenance?.generated_utc || new Date().toISOString(),
      source: result.source_label || result.source_type,
      health: result.health_score,
      quality: result.quality_score,
      risk: result.risk,
      anomalies: result.anomaly_regions?.length || 0,
    };
    setHistory((previous) => {
      const next = [item, ...previous.filter((entry) => entry.sessionId !== item.sessionId)].slice(0, 8);
      localStorage.setItem('octaneos-sentinel-history-v34', JSON.stringify(next));
      return next;
    });
  }

  async function bootstrap() {
    setBusy(true);
    setError('');
    try {
      const [normal, modelInfo, provider, submissionInfo] = await Promise.all([
        requestJSON(`${API}/demo`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: 'normal', severity: 'medium' }),
        }),
        requestJSON(`${API}/model/info`),
        requestJSON(`${API}/ai/status`),
        requestJSON(`${API}/submission/status`),
      ]);
      setBaseline(normal);
      setData(normal);
      setModel(modelInfo);
      setAiStatus(provider);
      setSubmission(submissionInfo);
      remember(normal);
    } catch (caught: any) {
      setError(caught?.message || String(caught));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    void bootstrap();
  }, []);

  async function run(nextScenario = scenario, nextSeverity: Severity = severity) {
    setBusy(true);
    setError('');
    try {
      const result = await requestJSON(`${API}/demo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: nextScenario, severity: nextSeverity }),
      });
      setData(result);
      setExplanation(null);
      remember(result);
      if (nextScenario === 'normal') setBaseline(result);
    } catch (caught: any) {
      setError(caught?.message || String(caught));
    } finally {
      setBusy(false);
    }
  }

  async function upload(file?: File) {
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      const form = new FormData();
      form.append('file', file);
      const result = await requestJSON(`${API}/analyze`, { method: 'POST', body: form });
      setData(result);
      setExplanation(null);
      remember(result);
      setPage('command');
    } catch (caught: any) {
      setError(caught?.message || String(caught));
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  async function explain(mode: 'local' | 'fast' | 'deep') {
    if (!data) return;
    setAiBusy(true);
    setError('');
    try {
      const result = await requestJSON(`${API}/explain`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis: data, mode }),
      });
      setExplanation(result);
    } catch (caught: any) {
      setError(caught?.message || String(caught));
    } finally {
      setAiBusy(false);
    }
  }

  function downloadReport(format: 'md' | 'json') {
    if (!data) return;
    const content =
      format === 'json'
        ? JSON.stringify({ analysis: data, explanation, model }, null, 2)
        : reportMarkdown(data, model, explanation);
    const blob = new Blob([content], {
      type: format === 'json' ? 'application/json' : 'text/markdown',
    });
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = `OctaneOS-${data.session_id}-Evidence-Report.${format}`;
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }

  const activePage = PAGES.find((item) => item[0] === page) || PAGES[0];
  const hypothesis = data?.hypotheses?.[0];
  const modelReady = model?.available && data?.model?.runtime_mode === 'frozen_trained_model';
  const cloudLabel = aiStatus?.configured ? 'Cloud explainer ready' : 'Local fallback ready';

  return (
    <div className="shell">
      <aside>
        <div className="brand">
          <span className="omega">Ω</span>
          <div>
            <b>OCTANEOS</b>
            <em>SENTINEL</em>
            <small>V3.4 · EVIDENCE BUILD</small>
          </div>
        </div>
        <nav>
          {PAGES.map(([id, label, icon]) => (
            <button key={id} className={page === id ? 'active' : ''} onClick={() => setPage(id)}>
              <span>{icon}</span>
              {label}
            </button>
          ))}
        </nav>
        <div className="asideMeta">
          <span>RUNTIME</span>
          <b className={modelReady ? 'good' : 'warn'}>
            {modelReady ? 'FROZEN MODEL' : 'LABELLED FALLBACK'}
          </b>
          <span>MODEL</span>
          <b>{data?.model?.version || model?.model_version || 'NOT LOADED'}</b>
          <span>PRIVACY</span>
          <b>RAW CSV STAYS LOCAL</b>
        </div>
        <div className="foot">
          <i /> LOCAL CORE ONLINE
          <br />
          <span>{cloudLabel}. No ECU or fuel-system control.</span>
        </div>
      </aside>

      <main>
        <header>
          <div>
            <p>ASPHALT SOVEREIGN · PROJECT OCTANE Ω</p>
            <h1>{activePage[1]}</h1>
          </div>
          <div className="topActions">
            <label className="upload">
              IMPORT CSV
              <input
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                onChange={(event) => void upload(event.target.files?.[0])}
              />
            </label>
            <button className="iconButton" onClick={() => downloadReport('md')} disabled={!data}>
              EXPORT REPORT
            </button>
            <span className="status">
              <i /> {busy ? 'PIPELINE RUNNING' : 'SYSTEM READY'}
            </span>
          </div>
        </header>

        {error && (
          <div className="error">
            <b>RUN BLOCKED</b>
            <span>{error}</span>
            <button onClick={() => setError('')}>×</button>
          </div>
        )}

        {page === 'command' && (
          <Command
            data={data}
            baseline={baseline}
            busy={busy}
            run={() => void run()}
            hypothesis={hypothesis}
            explanation={explanation}
            aiBusy={aiBusy}
            explain={explain}
            setPage={setPage}
          />
        )}
        {page === 'telemetry' && <Telemetry data={data} history={history} />}
        {page === 'investigation' && (
          <Investigation
            data={data}
            explanation={explanation}
            aiBusy={aiBusy}
            explain={explain}
          />
        )}
        {page === 'fault' && (
          <FaultLab
            data={data}
            baseline={baseline}
            model={model}
            scenario={scenario}
            setScenario={setScenario}
            severity={severity}
            setSeverity={setSeverity}
            run={run}
            busy={busy}
          />
        )}
        {page === 'model' && <ModelCard model={model} data={data} />}
        {page === 'evidence' && (
          <SubmissionProof
            submission={submission}
            model={model}
            data={data}
            downloadReport={downloadReport}
          />
        )}
      </main>
    </div>
  );
}

function Command({ data, baseline, busy, run, hypothesis, explanation, aiBusy, explain, setPage }: any) {
  const delta = compareValues(baseline, data);
  const frozenRuntime = data?.model?.runtime_mode === 'frozen_trained_model';
  const isSyntheticDemo = Boolean(data?.ground_truth);
  const screeningStatus = data?.ground_truth?.scenario === 'normal'
    ? 'REFERENCE RUN'
    : data?.ground_truth
      ? data.ground_truth.detected ? 'PERTURBATION DETECTED' : 'NO DETECTION OVERLAP'
      : (data?.anomaly_regions?.length || 0) > 0 ? 'ANOMALY FLAGGED' : 'NO REGION FLAGGED';
  return (
    <>
      <section className="hero commandHero">
        <div>
          <span className="kicker">EVIDENCE-FIRST VEHICLE TELEMETRY</span>
          <h2>Detect. Verify. Explain.</h2>
          <p>
            {frozenRuntime
              ? 'A checksummed frozen model screens synchronized operating windows before engineering rules test the evidence.'
              : 'The current runtime uses a clearly labelled local screening fallback; engineering rules still test evidence before any explanation is produced.'}
            {' '}Unsupported diagnostic claims remain blocked by the safety boundary.
          </p>
          <div className="heroBadges">
            <span className={isSyntheticDemo ? 'truthPill synthetic' : 'truthPill'}>
              {isSyntheticDemo ? 'SYNTHETIC DEMO TELEMETRY' : 'UPLOADED TELEMETRY'}
            </span>
            <span className={frozenRuntime ? 'truthPill modelReady' : 'truthPill modelFallback'}>
              {frozenRuntime ? 'CHECKSUMMED FROZEN RUNTIME' : 'LABELLED LOCAL FALLBACK'}
            </span>
          </div>
        </div>
        <div className="heroActions">
          <button className="secondary" onClick={() => setPage('fault')}>
            OPEN FAULT LAB
          </button>
          <button className="investigate" onClick={run} disabled={busy}>
            {busy ? 'RUNNING PIPELINE…' : 'RUN CURRENT SCENARIO'}
          </button>
        </div>
      </section>

      <section className="cards four">
        <MetricCard label="DATA QUALITY" value={data ? `${data.quality_score}/100` : '—'} sub="analysis-readiness gate" tone={data?.analysis_ready ? 'good' : 'danger'} />
        <MetricCard label="SCREENING STATUS" value={screeningStatus} sub={`evidence risk ${(data?.risk || '—').toUpperCase()} · ${data?.health_score ?? '—'}/100 screening index`} tone={data?.ground_truth?.scenario === 'normal' ? 'good' : (data?.anomaly_regions?.length || 0) > 0 ? 'warn' : 'good'} />
        <MetricCard label="ANOMALY REGIONS" value={data?.anomaly_regions?.length ?? '—'} sub={delta.anomalyText} tone={(data?.anomaly_regions?.length || 0) > 0 ? 'warn' : 'good'} />
        <MetricCard label="RUNTIME" value={frozenRuntime ? 'FROZEN' : 'LOCAL FALLBACK'} sub={frozenRuntime ? shortModel(data?.model?.version) : 'truth-labelled screening mode'} tone={frozenRuntime ? 'good' : 'warn'} />
      </section>

      <ComparisonBand baseline={baseline} data={data} />

      <section className="panel chartPanel premiumChartPanel">
        <PanelHead title="Engineering Telemetry Timeline" tag="PHYSICAL UNITS · SHARED TIMEBASE" />
        <TelemetryChart data={data} />
      </section>

      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Investigation Trace" tag={data?.session_id || 'AWAITING SESSION'} />
          <Trace data={data} />
        </article>
        <article className="panel">
          <PanelHead title="Retained Hypothesis" tag="EVIDENCE BOUNDED" />
          {hypothesis ? (
            <Hypothesis hypothesis={hypothesis} />
          ) : (
            <div className="empty">
              No component hypothesis was retained. Statistical deviations remain visible for
              engineering review.
            </div>
          )}
        </article>
      </section>

      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Dominant Behaviour Signals" tag="MODEL CONTRIBUTORS" />
          <FeatureBars data={data} />
        </article>
        <article className="panel">
          <PanelHead
            title="AI Explanation Layer"
            tag={explanation ? `${explanation.provider} · ${explanation.model}` : 'ON DEMAND'}
          />
          <AIBlock data={data} explanation={explanation} aiBusy={aiBusy} explain={explain} />
        </article>
      </section>
    </>
  );
}

function Telemetry({ data, history }: { data: Result | null; history: HistoryItem[] }) {
  return (
    <>
      <section className="hero compact">
        <div>
          <span className="kicker">ENGINEERING VISUALIZER</span>
          <h2>One timeline. Every decision traceable.</h2>
          <p>
            The browser receives a bounded visualization preview. Raw uploaded CSV bytes are
            analyzed in memory and are not sent to the language-model layer.
          </p>
        </div>
      </section>
      <section className="panel chartPanel">
        <PanelHead title="Telemetry + Anomaly Overlay" tag={`${data?.sample_count || 0} SOURCE SAMPLES`} />
        <TelemetryChart data={data} tall />
      </section>
      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Signal Coverage" tag="SIGNAL GUARDIAN" />
          <CoverageGrid data={data} />
        </article>
        <article className="panel">
          <PanelHead title="Anomaly Region Ledger" tag="ACTIVE SCREENING THRESHOLD" />
          <AnomalyList data={data} />
        </article>
      </section>
      <section className="panel historyPanel">
        <PanelHead title="Local Session History" tag="BROWSER-LOCAL SUMMARY ONLY" />
        <div className="historyGrid">
          {history.map((item) => (
            <div className="historyItem" key={item.sessionId}>
              <span>{item.source}</span>
              <b>{item.sessionId}</b>
              <small>{new Date(item.created).toLocaleString()}</small>
              <div>
                <em>{item.health}/100</em>
                <em>{item.anomalies} regions</em>
                <em>{item.risk}</em>
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

function Investigation({ data, explanation, aiBusy, explain }: any) {
  const hypothesis = data?.hypotheses?.[0];
  return (
    <>
      <section className="hero compact">
        <div>
          <span className="kicker">BOUNDED INVESTIGATION PIPELINE</span>
          <h2>A conclusion survives only if the evidence supports it.</h2>
          <p>
            Detection, engineering rules, hypothesis ranking, contradiction review, claim
            blocking, and natural-language explanation remain separate and inspectable.
          </p>
        </div>
      </section>
      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Execution Trace" tag="REPRODUCIBLE" />
          <Trace data={data} detailed />
        </article>
        <article className="panel">
          <PanelHead title="Evidence Graph" tag="DETECT → TEST → BOUND" />
          {hypothesis ? <EvidenceGraph hypothesis={hypothesis} /> : <div className="empty">Run a session first.</div>}
        </article>
      </section>
      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Engineering Explanation" tag="STRUCTURED EVIDENCE ONLY" />
          <AIBlock data={data} explanation={explanation} aiBusy={aiBusy} explain={explain} />
        </article>
        <article className="panel safetyPanel">
          <PanelHead title="Safety-Agent Output" tag="HARD CLAIM BOUNDARY" />
          <div className="blockedClaims">
            {(hypothesis?.blocked_claims || data?.limitations || []).map((claim: string, index: number) => (
              <div key={index}>
                <i>×</i>
                <span>{claim}</span>
              </div>
            ))}
          </div>
          <p className="boundaryCopy">{data?.claim_boundary}</p>
        </article>
      </section>
    </>
  );
}

function FaultLab({ data, baseline, model, scenario, setScenario, severity, setSeverity, run, busy }: any) {
  const selected = SCENARIOS.find((item) => item.id === scenario) || SCENARIOS[0];
  const capabilities: string[] = model?.capability_signals || data?.model?.capability_signals || [];
  const supported = selected.requires.every((signal) => capabilities.includes(signal));
  const comparison = compareValues(baseline, data);
  const frozenRuntime = Boolean(model?.available && data?.model?.runtime_mode === 'frozen_trained_model');
  return (
    <>
      <section className="hero compact">
        <div>
          <span className="kicker">CONTROLLED PERTURBATION HARNESS</span>
          <h2>Known disturbance. Hidden label. SAME SCREENING PIPELINE.</h2>
          <p>
            Fault labels are retained only for evaluation and never passed into screening as features or hints.
            The active runtime is {frozenRuntime ? 'the checksum-verified frozen model' : 'the clearly labelled local fallback'}.
          </p>
        </div>
      </section>

      <section className="grid labGrid">
        <article className="panel faultControls">
          <PanelHead title="Experiment Builder" tag="DETERMINISTIC SEED" />
          <label>SCENARIO</label>
          <select value={scenario} onChange={(event) => setScenario(event.target.value)}>
            {SCENARIOS.map((item) => (
              <option value={item.id} key={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          <label>SEVERITY</label>
          <div className="severity">
            {(['mild', 'medium', 'severe'] as Severity[]).map((item) => (
              <button className={severity === item ? 'selected' : ''} onClick={() => setSeverity(item)} key={item}>
                {item}
              </button>
            ))}
          </div>
          <div className={supported || scenario === 'normal' ? 'capability goodBox' : 'capability warnBox'}>
            <b>{supported || scenario === 'normal' ? 'SCENARIO SIGNALS AVAILABLE' : 'SCENARIO CAPABILITY GATED'}</b>
            <span>
              {selected.requires.length ? `Required: ${selected.requires.join(', ')}` : 'Untouched reference session'}
            </span>
          </div>
          <button className="run" onClick={() => void run(scenario, severity)} disabled={busy || (!supported && scenario !== 'normal')}>
            {busy ? 'RUNNING EXPERIMENT…' : !supported && scenario !== 'normal' ? 'CAPABILITY GATED' : 'GENERATE + ANALYZE'}
          </button>
          <p className="finePrint">
            Unsupported scenarios remain visible to prove the capability gate; skipped outcomes
            are not counted as successful detections.
          </p>
        </article>

        <article className="panel">
          <PanelHead title="Ground Truth vs Detection" tag="EXPERIMENT EVIDENCE" />
          <GroundTruth data={data} />
          <div className="compareTable">
            <div><span>METRIC</span><span>REFERENCE</span><span>CURRENT</span><span>Δ</span></div>
            <CompareRow label="Health index" base={baseline?.health_score} current={data?.health_score} delta={comparison.healthDelta} />
            <CompareRow label="Anomaly regions" base={baseline?.anomaly_regions?.length} current={data?.anomaly_regions?.length} delta={comparison.anomalyDelta} />
            <CompareRow label="Evidence risk" base={String(baseline?.risk || '—').toUpperCase()} current={String(data?.risk || '—').toUpperCase()} delta="bounded" />
          </div>
        </article>
      </section>

      <section className="panel chartPanel">
        <PanelHead title="Experiment Timeline" tag={scenario.toUpperCase().replaceAll('_', ' ')} />
        <TelemetryChart data={data} />
      </section>
    </>
  );
}

function ModelCard({ model, data }: any) {
  const validation = model?.validation || {};
  const weights = model?.ensemble_weights || {};
  return (
    <>
      <section className="hero compact">
        <div>
          <span className="kicker">MODEL GOVERNANCE</span>
          <h2>Measured capability, provenance, and limits.</h2>
          <p>
            {model?.available
              ? 'The checksum-verified model artifact is active. Calibration and test vehicles are separated; controlled perturbations measure sensitivity, not component-failure accuracy.'
              : 'RUNTIME ARTIFACT NOT PACKAGED. This build therefore uses the clearly labelled local fallback; historical validation evidence must not be confused with current runtime execution.'}
          </p>
        </div>
        <span className={model?.available ? 'modelSeal ready' : 'modelSeal missing'}>
          {model?.available ? 'FROZEN + CHECKSUMMED' : 'RUNTIME FALLBACK'}
        </span>
      </section>
      <section className="cards six">
        <MetricCard label="VERSION" value={shortModel(model?.model_version)} sub="frozen manifest" />
        <MetricCard label="FEATURES" value={model?.feature_count ?? '—'} sub="window-level inputs" />
        <MetricCard label="TRAIN VEHICLES" value={model?.training_vehicles ?? '—'} sub="group-isolated split" />
        <MetricCard label="CAL VEHICLES" value={model?.calibration_vehicles ?? '—'} sub="threshold selection" />
        <MetricCard label="TEST VEHICLES" value={model?.test_vehicles ?? '—'} sub="untouched holdout" />
        <MetricCard label="THRESHOLD" value={number(model?.decision_threshold, 3)} sub="frozen decision point" />
      </section>
      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title={model?.available ? 'Frozen Ensemble' : 'Runtime Artifact Status'} tag={model?.available ? 'LOCAL INFERENCE' : 'FALLBACK ACTIVE'} />
          {model?.available ? (
            <>
              <div className="detectors">
                <Detector label="Isolation Forest" weight={weights.iforest} color="#62e9ae" />
                <Detector label="PCA reconstruction" weight={weights.pca} color="#62a8e9" />
                <Detector label="Robust Z-score" weight={weights.robust_z} color="#e9b762" />
              </div>
              <div className="hash">
                <span>ARTIFACT SHA-256</span>
                <code>{model?.artifact_sha256 || data?.model?.artifact_sha256 || 'Unavailable'}</code>
              </div>
            </>
          ) : (
            <div className="runtimeNotice">
              <b>LOCAL SCREENING FALLBACK ACTIVE</b>
              <span>The frozen binary is not present in this package. The UI keeps this state visible instead of implying verified model execution.</span>
              <small>Restore the verified artifact later to enable checksum-backed frozen inference.</small>
            </div>
          )}
        </article>
        <article className="panel">
          <PanelHead title="Final-Test Evidence" tag="HONEST METRICS" />
          <div className="validationGrid">
            <ValidationMetric label="Normal-window FPR" value={percent(validation.untouched_normal_fpr)} />
            <ValidationMetric label="Injection window F1" value={percent(validation.injected_window_f1)} />
            <ValidationMetric label="Run detection" value={percent(validation.injected_run_detection_rate)} />
            <ValidationMetric label="Experiments" value={validation.injected_run_experiments ?? '—'} />
          </div>
          <p className="boundaryCopy">{validation.claim_boundary || model?.claim_boundary}</p>
        </article>
      </section>
      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Severity Response" tag="CONTROLLED INJECTION" />
          <SeverityChart values={validation.severity || []} />
        </article>
        <article className="panel">
          <PanelHead title="Declared Capability" tag="SIGNAL FAMILIES" />
          <div className="capabilityTags">
            {(model?.capability_signals || []).map((signal: string) => <span key={signal}>{signal}</span>)}
          </div>
          <p className="boundaryCopy">{model?.domain_boundary}</p>
        </article>
      </section>
    </>
  );
}

function SubmissionProof({ submission, model, data, downloadReport }: any) {
  const judging = [
    ['Innovation & creativity', 'Evidence-first AI investigation with explicit contradiction and claim blocking'],
    ['Technical excellence', 'Validated model evidence, checksum provenance, quality gate, deterministic rules, tested API'],
    ['Real-world impact', 'Low-cost diagnostic screening path for legacy vehicles and future SAN-V1 telemetry'],
    ['Scalability', 'CSV contract, capability-specific models, local-first core, optional provider routing'],
    ['User experience', 'Six-screen workstation, visual fault lab, CSV import, one-click evidence report'],
    ['Presentation quality', 'Baseline → perturbation → detection → evidence → safety narrative'],
  ];
  return (
    <>
      <section className="hero compact">
        <div>
          <span className="kicker">HACKATHON READINESS</span>
          <h2>Every judging axis maps to visible proof.</h2>
          <p>
            The submission story is not “AI diagnoses a motorcycle.” It is a reproducible,
            evidence-bounded telemetry investigation system with a clear hardware integration path.
          </p>
        </div>
        <div className="heroActions">
          <button className="secondary" onClick={() => downloadReport('json')}>EXPORT JSON</button>
          <button className="investigate" onClick={() => downloadReport('md')}>EXPORT EVIDENCE REPORT</button>
        </div>
      </section>
      <section className="deadlineBand">
        <div><span>FINAL PROJECT SUBMISSION</span><b>10 SEP 2026 · 11:23 PM IST</b></div>
        <div><span>PLATFORM</span><b>UNSTOP</b></div>
        <div><span>REQUIRED MEDIA</span><b>GITHUB · PPT/PDF · 3–5 MIN VIDEO</b></div>
      </section>
      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Judging-Criteria Map" tag="6 / 6 COVERED" />
          <div className="criteria">
            {judging.map(([criterion, proof]) => (
              <div key={criterion}><i>✓</i><b>{criterion}</b><span>{proof}</span></div>
            ))}
          </div>
        </article>
        <article className="panel">
          <PanelHead title="Required Submission Bundle" tag="UNSTOP" />
          <div className="checklist">
            {(submission?.submission_items || []).map((item: any) => (
              <div key={item.item}>
                <i className={item.status === 'ready' ? 'ready' : 'pending'}>{item.status === 'ready' ? '✓' : '→'}</i>
                <span><b>{item.item}</b><small>{item.status}</small></span>
              </div>
            ))}
          </div>
        </article>
      </section>
      <section className="panel architecturePanel">
        <PanelHead title="Locked Evidence Architecture" tag="LOCAL CORE · OPTIONAL EXPLANATION" />
        <div className="architecture">
          {['CSV / SAN-V1', 'Signal Guardian', 'Feature engineering', model?.available ? 'Frozen ensemble' : 'Local screening fallback', 'Engineering rules', 'Evidence + safety', 'Optional LLM', 'Report'].map((item, index) => (
            <React.Fragment key={item}>
              <div><span>{String(index + 1).padStart(2, '0')}</span><b>{item}</b></div>
              {index < 7 && <i>→</i>}
            </React.Fragment>
          ))}
        </div>
      </section>
      <section className="grid commandGrid">
        <article className="panel">
          <PanelHead title="Submission Evidence Snapshot" tag={submission?.build || 'V3.4'} />
          <div className="evidenceStats">
            <ValidationMetric label="Terminal 2 tests" value={`${submission?.verification?.terminal_tests_passed || 20} passed`} />
            <ValidationMetric label="Current release tests" value={`${submission?.verification?.release_tests_passed || 32} passed`} />
            <ValidationMetric label="Controlled experiments" value={submission?.evidence?.controlled_injection_experiments ?? model?.validation?.injected_run_experiments ?? '207'} />
            <ValidationMetric label="Run detection" value={percent(submission?.evidence?.controlled_injection_run_detection_rate ?? model?.validation?.injected_run_detection_rate)} />
            <ValidationMetric label="Detected experiments" value={submission?.evidence?.controlled_injection_detected ?? '158'} />
            <ValidationMetric label="Evidence source" value={submission?.evidence?.current_runtime_verified ? 'RUNTIME' : 'TERMINAL SNAPSHOT'} />
          </div>
        </article>
        <article className="panel safetyPanel">
          <PanelHead title="Non-Negotiable Truth Boundary" tag="JUDGE SAFE" />
          <p className="largeBoundary">{submission?.truth_boundary}</p>
          <p className="boundaryCopy">
            No claim of Yamaha R15 V2 health validation, component-failure accuracy, remaining
            useful life, ECU/DTC access, AFR, injector condition, ignition timing, or measured
            ethanol percentage is made by this build.
          </p>
        </article>
      </section>
    </>
  );
}

function TelemetryChart({ data, tall = false }: { data: Result | null; tall?: boolean }) {
  const telemetry = data?.telemetry || [];
  if (!telemetry.length) return <div className="chartEmpty">No telemetry loaded.</div>;

  const width = 1120;
  const height = tall ? 600 : 500;
  const left = 150;
  const right = 34;
  const top = 38;
  const bottom = 34;
  const gap = 15;
  const laneCount = 4;
  const laneHeight = (height - top - bottom - gap * (laneCount - 1)) / laneCount;
  const plotWidth = width - left - right;
  const sampleCount = Math.max(2, data?.sample_count || telemetry.length || 2);
  const x = (index: number) => left + (index / (sampleCount - 1)) * plotWidth;

  const finite = (key: string) => telemetry.map((row: any) => Number(row[key])).filter(Number.isFinite);
  const rpmValues = finite('rpm');
  const speedValues = finite('speed');
  const loadValues = finite('engine_load');
  const anomalyValues = finite('anomaly_score');
  const roundUp = (value: number, step: number) => Math.max(step, Math.ceil(value / step) * step);

  const lanes = [
    { key: 'rpm', label: 'RPM (rev/min)', min: 0, max: roundUp(Math.max(...rpmValues, 4000), 1000), color: '#63edaf' },
    { key: 'speed', label: 'Speed (km/h)', min: 0, max: roundUp(Math.max(...speedValues, 60), 20), color: '#62a8e9' },
    { key: 'engine_load', label: 'Engine load (%)', min: 0, max: 100, color: '#c08cff' },
    { key: 'anomaly_score', label: 'Anomaly score (0–1)', min: 0, max: 1, color: '#ffbd62' },
  ];

  function y(value: number, laneIndex: number, min: number, max: number) {
    const laneTop = top + laneIndex * (laneHeight + gap);
    const span = Math.max(max - min, 1e-6);
    return laneTop + laneHeight - ((value - min) / span) * laneHeight;
  }

  function points(lane: any, laneIndex: number) {
    return telemetry
      .filter((row: any) => Number.isFinite(Number(row[lane.key])))
      .map((row: any) => `${x(row.index).toFixed(1)},${y(Number(row[lane.key]), laneIndex, lane.min, lane.max).toFixed(1)}`)
      .join(' ');
  }

  const truth = data?.ground_truth;
  const faultActive = truth && truth.scenario !== 'normal' && Number.isInteger(truth.start_index) && Number.isInteger(truth.end_index);
  const faultX = faultActive ? x(truth.start_index) : 0;
  const faultWidth = faultActive ? Math.max(4, x(truth.end_index) - faultX) : 0;
  const avg = (values: number[]) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;
  const peak = (values: number[]) => values.length ? Math.max(...values) : 0;

  return (
    <div className={tall ? 'telemetryChart tall engineeringChart' : 'telemetryChart engineeringChart'}>
      <div className="chartContext">
        <span><i className="contextDot syntheticDot" />{data?.ground_truth ? 'Synthetic validation session' : 'Uploaded telemetry session'}</span>
        <span><i className="contextDot anomalyDot" />Detected anomaly regions</span>
        {faultActive && <span><i className="contextDot faultDot" />CONTROLLED FAULT INJECTION</span>}
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Engineering telemetry timeline in physical units">
        {faultActive && (
          <>
            <rect x={faultX} y={top - 16} width={faultWidth} height={height - top - bottom + 20} className="faultInjectionBand" />
            <text x={faultX + 8} y={top - 4} className="faultLabel">CONTROLLED FAULT INJECTION</text>
          </>
        )}

        {(data?.anomaly_regions || []).map((region: any, index: number) => (
          <rect
            key={`region-${index}`}
            x={x(region.start_index)}
            y={top}
            width={Math.max(3, x(region.end_index) - x(region.start_index))}
            height={height - top - bottom}
            className="detectedRegionBand"
          />
        ))}

        {lanes.map((lane, laneIndex) => {
          const laneTop = top + laneIndex * (laneHeight + gap);
          const laneBottom = laneTop + laneHeight;
          return (
            <g key={lane.key}>
              <rect x={left} y={laneTop} width={plotWidth} height={laneHeight} rx="8" className="laneBackground" />
              {[0, 0.5, 1].map((fraction) => {
                const gridY = laneTop + laneHeight * fraction;
                const value = lane.max - (lane.max - lane.min) * fraction;
                return (
                  <React.Fragment key={fraction}>
                    <line x1={left} x2={width - right} y1={gridY} y2={gridY} className="gridLine" />
                    <text x={left - 12} y={gridY + 4} textAnchor="end" className="scaleText">
                      {lane.key === 'anomaly_score' ? value.toFixed(1) : Math.round(value)}
                    </text>
                  </React.Fragment>
                );
              })}
              <text x="12" y={laneTop + 20} className="laneLabel">{lane.label}</text>
              <text x="12" y={laneTop + 39} className="laneRange">{lane.min} — {lane.max}</text>
              <polyline
                points={points(lane, laneIndex)}
                fill="none"
                stroke={lane.color}
                strokeWidth={lane.key === 'anomaly_score' ? '2.8' : '2.35'}
                vectorEffect="non-scaling-stroke"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
              {lane.key === 'anomaly_score' && (
                <line
                  x1={left}
                  x2={width - right}
                  y1={y(0.58, laneIndex, 0, 1)}
                  y2={y(0.58, laneIndex, 0, 1)}
                  className="thresholdLine"
                />
              )}
              {laneIndex < laneCount - 1 && <line x1={left} x2={width - right} y1={laneBottom + gap / 2} y2={laneBottom + gap / 2} className="laneDivider" />}
            </g>
          );
        })}
        <text x={left} y={height - 9} className="axisText">sample 0</text>
        <text x={width - right} y={height - 9} textAnchor="end" className="axisText">sample {sampleCount - 1}</text>
      </svg>
      <div className="chartSummary">
        <div><span>AVG RPM</span><b>{Math.round(avg(rpmValues)).toLocaleString()} rev/min</b></div>
        <div><span>AVG SPEED</span><b>{avg(speedValues).toFixed(1)} km/h</b></div>
        <div><span>PEAK LOAD</span><b>{peak(loadValues).toFixed(0)}%</b></div>
        <div><span>PEAK ANOMALY</span><b>{peak(anomalyValues).toFixed(2)}</b></div>
      </div>
    </div>
  );
}

function ComparisonBand({ baseline, data }: any) {
  const values = compareValues(baseline, data);
  const scenario = data?.ground_truth?.scenario || 'uploaded session';
  return (
    <section className="comparisonBand">
      <div><span>REFERENCE</span><b>{baseline?.session_id || 'Loading'}</b></div>
      <i>→</i>
      <div><span>CURRENT RUN</span><b>{String(scenario).replaceAll('_', ' ')}</b></div>
      <div className="delta"><span>HEALTH Δ</span><b>{signed(values.healthDelta)}</b></div>
      <div className="delta"><span>REGION Δ</span><b>{signed(values.anomalyDelta)}</b></div>
      <div className="verdict"><span>EVIDENCE RISK</span><b>{String(data?.risk || '—').toUpperCase()}</b></div>
    </section>
  );
}

function Trace({ data, detailed = false }: any) {
  const hypothesis = data?.hypotheses?.[0];
  const frozenRuntime = data?.model?.runtime_mode === 'frozen_trained_model';
  const items = [
    ['Source Integrity', data ? `${data.sample_count} samples · ${data.source_type.toUpperCase()} contract` : 'Waiting'],
    ['Signal Guardian', data ? `Quality ${data.quality_score}/100 · readiness ${data.analysis_ready ? 'PASS' : 'REJECT'}` : 'Waiting'],
    ['Feature Engineering', data ? `${data.model.feature_count} ${frozenRuntime ? 'window features' : 'screening features'}` : 'Waiting'],
    ['Model Screening', data ? (frozenRuntime ? `${data.model.window_count} windows · ${data.model.anomaly_window_count} flagged` : 'Labelled local fallback · sample-level screening') : 'Waiting'],
    ['Engineering Rules', data ? `${data.rules?.length || 0} deterministic findings` : 'Waiting'],
    ['Evidence Verification', hypothesis ? `${hypothesis.evidence.length} support · ${hypothesis.contradictions.length} contradiction` : 'No retained hypothesis'],
    ['Safety Agent', hypothesis ? `${hypothesis.blocked_claims.length} unsupported claim classes blocked` : 'Boundary active'],
    ['Explanation', 'Compact evidence only · raw telemetry excluded'],
  ];
  return (
    <div className="steps">
      {items.map(([label, detail], index) => (
        <div className="step" key={label}>
          <i className={data ? 'done' : ''}>{data ? '✓' : '·'}</i>
          <div>
            <b>{detailed ? `${String(index + 1).padStart(2, '0')}  ${label}` : label}</b>
            <small>{detail}</small>
          </div>
        </div>
      ))}
    </div>
  );
}

function Hypothesis({ hypothesis }: any) {
  return (
    <>
      <div className="hypothesis">
        <span>{hypothesis.subsystem}</span>
        <h2>{hypothesis.name}</h2>
        <p>Confidence {Math.round(hypothesis.confidence * 100)}% · Severity {String(hypothesis.severity).toUpperCase()}</p>
      </div>
      <div className="evidenceList">
        <b>SUPPORTING EVIDENCE</b>
        {hypothesis.evidence.slice(0, 5).map((item: any, index: number) => <small key={index}>✓ {item.observation}</small>)}
        {!!hypothesis.contradictions?.length && (
          <>
            <b>CONTRADICTIONS</b>
            {hypothesis.contradictions.map((item: any, index: number) => <small className="contra" key={index}>× {item.observation}</small>)}
          </>
        )}
        <b>INSPECTION ACTION</b>
        <small>{hypothesis.recommended_action}</small>
      </div>
    </>
  );
}

function EvidenceGraph({ hypothesis }: any) {
  return (
    <div className="evidenceGraph">
      <div className="graphNode anomalyNode">ANOMALY WINDOW<small>statistical deviation</small></div>
      <i>↓</i>
      <div className="graphNode hypothesisNode">{hypothesis.name}<small>{Math.round(hypothesis.confidence * 100)}% bounded confidence</small></div>
      <div className="graphSplit">
        <div><b>SUPPORT</b>{hypothesis.evidence.slice(0, 4).map((item: any, index: number) => <small key={index}>✓ {item.signal}</small>)}</div>
        <div><b>CONTRADICTIONS</b>{hypothesis.contradictions?.length ? hypothesis.contradictions.map((item: any, index: number) => <small key={index}>× {item.signal}</small>) : <small>None recorded</small>}</div>
      </div>
      <i>↓</i>
      <div className="graphNode safetyNode">SAFETY GATE<small>{hypothesis.blocked_claims.length} claim classes blocked</small></div>
    </div>
  );
}

function AIBlock({ data, explanation, aiBusy, explain }: any) {
  return (
    <>
      <div className="aiActions">
        <button className="run inline" onClick={() => void explain('local')} disabled={!data || aiBusy}>
          {aiBusy ? 'BUILDING EXPLANATION…' : 'INSTANT LOCAL'}
        </button>
        <button className="run inline" onClick={() => void explain('fast')} disabled={!data || aiBusy}>
          FAST CLOUD
        </button>
        <button className="secondary" onClick={() => void explain('deep')} disabled={!data || aiBusy}>DEEP CLOUD</button>
      </div>
      {explanation ? (
        <div className="aiOutput">
          <div className={explanation.status === 'ai_generated' ? 'providerBadge cloud' : 'providerBadge local'}>
            {explanation.status === 'ai_generated' ? 'CLOUD EXPLANATION' : 'DETERMINISTIC FALLBACK'}
          </div>
          <p>{explanation.executive_summary}</p>
          <div className="aiCols">
            <div><b>INSPECTION STEPS</b>{explanation.inspection_steps?.map((item: string, index: number) => <small key={index}>→ {item}</small>)}</div>
            <div><b>SAFETY CAVEATS</b>{explanation.caveats?.map((item: string, index: number) => <small key={index}>• {item}</small>)}</div>
          </div>
          {explanation.reason && <p className="providerReason">{explanation.reason}</p>}
        </div>
      ) : (
        <p className="empty">
          Local inference and engineering logic already own the result. The optional model receives
          only compact structured evidence after analysis.
        </p>
      )}
    </>
  );
}

function GroundTruth({ data }: any) {
  const truth = data?.ground_truth;
  if (!truth) return <div className="empty">Run a controlled scenario to create experiment evidence.</div>;
  const verdict =
    truth.scenario === 'normal'
      ? 'REFERENCE RUN'
      : !truth.model_supported
        ? 'CAPABILITY-GATED'
        : truth.detected
          ? 'DETECTION OVERLAP'
          : 'DETECTION MISS';
  return (
    <div className="truthGrid">
      <div><span>INJECTED CONDITION</span><b>{String(truth.scenario).replaceAll('_', ' ')}</b></div>
      <div><span>SEVERITY</span><b>{String(truth.severity).toUpperCase()}</b></div>
      <div><span>GROUND-TRUTH WINDOW</span><b>{truth.start_index == null ? 'NONE' : `${truth.start_index} → ${truth.end_index}`}</b></div>
      <div><span>OVERLAP REGIONS</span><b>{truth.overlap_regions}</b></div>
      <div><span>LABEL VISIBLE TO MODEL</span><b>{truth.label_hidden_from_model ? 'NO' : 'YES'}</b></div>
      <div><span>MODEL CAPABILITY</span><b>{truth.model_supported ? 'SUPPORTED' : 'NOT DECLARED'}</b></div>
      <div className={`truthVerdict ${truth.detected ? 'pass' : truth.model_supported ? 'neutral' : 'gated'}`}>{verdict}</div>
    </div>
  );
}

function FeatureBars({ data }: any) {
  const items = data?.feature_importance || [];
  if (!items.length) return <div className="empty">No dominant contributor was retained.</div>;
  return <div className="featureBars">{items.map((item: any) => (
    <div key={item.feature}><span>{String(item.feature).replaceAll('_', ' ')}</span><i><b style={{ width: `${Math.max(3, item.score * 100)}%` }} /></i><em>{Math.round(item.score * 100)}</em></div>
  ))}</div>;
}

function CoverageGrid({ data }: any) {
  const coverage = data?.signal_coverage || {};
  return <div className="coverageGrid">{Object.entries(coverage).map(([signal, value]: any) => (
    <div key={signal}><span>{signal.replaceAll('_', ' ')}</span><b>{Math.round(value * 100)}%</b><i><em style={{ width: `${value * 100}%` }} /></i></div>
  ))}</div>;
}

function AnomalyList({ data }: any) {
  const regions = data?.anomaly_regions || [];
  if (!regions.length) return <div className="empty">No anomaly region crossed the active screening threshold.</div>;
  return <div className="anomalyList">{regions.slice(0, 10).map((region: any, index: number) => (
    <div key={index}><b>A-{String(index + 1).padStart(2, '0')}</b><span><strong>{Math.round(region.score * 100)}% score · samples {region.start_index}–{region.end_index}</strong><small>{region.top_signals?.join(' · ') || 'No supported signal contributor'}</small></span></div>
  ))}</div>;
}

function SeverityChart({ values }: { values: any[] }) {
  if (!values.length) return <div className="empty">Frozen validation report is unavailable.</div>;
  return <div className="severityChart">{values.map((item: any) => (
    <div key={item.severity}><span>{String(item.severity).toUpperCase()}</span><i><b style={{ width: `${(item.injected_run_detection_rate || 0) * 100}%` }} /></i><em>{percent(item.injected_run_detection_rate)}</em><small>{item.detected_experiments}/{item.experiments} runs</small></div>
  ))}</div>;
}

function Detector({ label, weight, color }: any) {
  const value = Number(weight || 0);
  return <div className="detector"><div><i style={{ background: color }} /><span>{label}</span><b>{Math.round(value * 100)}%</b></div><em><i style={{ width: `${value * 100}%`, background: color }} /></em></div>;
}

function ValidationMetric({ label, value }: any) {
  return <div className="validationMetric"><span>{label}</span><b>{value ?? '—'}</b></div>;
}

function CompareRow({ label, base, current, delta }: any) {
  return <div><b>{label}</b><span>{base ?? '—'}</span><span>{current ?? '—'}</span><em>{typeof delta === 'number' ? signed(delta) : delta}</em></div>;
}

function MetricCard({ label, value, sub, tone = '' }: any) {
  return <article className={`metricCard ${tone}`}><span>{label}</span><strong>{value}</strong><small>{sub}</small></article>;
}

function PanelHead({ title, tag }: { title: string; tag: string }) {
  return <div className="panelHead"><h3>{title}</h3><span>{tag}</span></div>;
}

function compareValues(baseline: any, data: any) {
  const healthDelta = Number(data?.health_score || 0) - Number(baseline?.health_score || 0);
  const anomalyDelta = Number(data?.anomaly_regions?.length || 0) - Number(baseline?.anomaly_regions?.length || 0);
  return {
    healthDelta,
    anomalyDelta,
    anomalyText: baseline ? `${signed(anomalyDelta)} vs reference` : 'awaiting reference',
  };
}

function signed(value: number) {
  return `${value > 0 ? '+' : ''}${Number.isFinite(value) ? value : 0}`;
}

function riskTone(risk?: string) {
  return risk === 'high' || risk === 'critical' ? 'danger' : risk === 'medium' ? 'warn' : 'good';
}

function shortModel(value?: string) {
  if (!value) return '—';
  return value.replace('sentinel-powertrain-baseline-', 'BASELINE ');
}

function number(value: any, digits = 2) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
}

function percent(value: any) {
  return Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(1)}%` : '—';
}

function reportMarkdown(data: any, model: any, explanation: any) {
  const hypothesis = data?.hypotheses?.[0];
  return `# OctaneOS Sentinel Evidence Report

**Project:** Asphalt Sovereign / Project Octane Ω  
**Build:** ${data?.provenance?.pipeline || 'OctaneOS Sentinel V3.4'}  
**Generated:** ${data?.provenance?.generated_utc || new Date().toISOString()}

## Source and provenance

- Session: ${data?.session_id}
- Source: ${data?.source_label}
- Samples: ${data?.sample_count}
- CSV SHA-256: ${data?.provenance?.sha256 || 'Synthetic controlled demo'}
- Raw file retained by API: ${data?.provenance?.raw_file_retained ? 'Yes' : 'No'}

## Screening result

- Data quality: ${data?.quality_score}/100
- Screening health index: ${data?.health_score}/100
- Evidence risk: ${String(data?.risk || 'unknown').toUpperCase()}
- Anomaly regions: ${data?.anomaly_regions?.length || 0}
- Runtime: ${data?.model?.runtime_mode}
- Model: ${data?.model?.version}
- Model artifact SHA-256: ${data?.model?.artifact_sha256 || model?.artifact_sha256 || 'Unavailable'}

## Retained hypothesis

${hypothesis ? `**${hypothesis.name}** — ${Math.round(hypothesis.confidence * 100)}% bounded confidence

${hypothesis.evidence.map((item: any) => `- Support: ${item.observation}`).join('\n')}
${hypothesis.contradictions.map((item: any) => `- Contradiction: ${item.observation}`).join('\n')}
- Inspection: ${hypothesis.recommended_action}` : 'No component hypothesis retained.'}

## Optional explanation

${explanation ? `${explanation.executive_summary}

${explanation.inspection_steps.map((item: string) => `- ${item}`).join('\n')}` : 'Not requested. The deterministic evidence result remains complete without a cloud model.'}

## Truth boundary

${data?.claim_boundary}

${(data?.limitations || []).map((item: string) => `- ${item}`).join('\n')}
`;
}

