import { useState, type ReactNode } from "react";
import {
  Activity,
  BarChart3,
  CalendarDays,
  Check,
  ChevronRight,
  CircleHelp,
  Clock3,
  CloudSun,
  HeartPulse,
  LayoutDashboard,
  MessageCircle,
  RefreshCw,
  Settings,
  Sparkles,
  Timer,
  TrendingUp,
  Trophy,
  X,
} from "lucide-react";

type Page = "dashboard" | "runs" | "chat" | "settings";
type RunStatus = "above" | "steady" | "easy";

type Run = {
  id: string;
  date: string;
  title: string;
  type: string;
  distance: string;
  pace: string;
  heartRate: string;
  duration: string;
  status: RunStatus;
  description: string;
};

const runs: Run[] = [
  {
    id: "benchmark-demo",
    date: "22 lis 2026",
    title: "Benchmark 5 min",
    type: "Test szybkości",
    distance: "1,01 km",
    pace: "4:57",
    heartRate: "169",
    duration: "05:00",
    status: "above",
    description: "Dobry sygnał szybkości. Ten wynik nie jest jeszcze samodzielną prognozą półmaratonu, ale daje mocny punkt odniesienia.",
  },
  {
    id: "easy-2026-11-20",
    date: "20 lis 2026",
    title: "Spokojny bieg",
    type: "Easy",
    distance: "6,42 km",
    pace: "6:31",
    heartRate: "143",
    duration: "41:50",
    status: "steady",
    description: "Równa praca i spokojne tętno. W drugiej połowie lekko wzrosło obciążenie, ale bez sygnału do zmiany planu.",
  },
  {
    id: "intervals-2026-11-18",
    date: "18 lis 2026",
    title: "Krótkie interwały",
    type: "Interwały",
    distance: "5,87 km",
    pace: "5:42",
    heartRate: "158",
    duration: "33:28",
    status: "easy",
    description: "Odcinki były wykonane dynamicznie, a przerwy pozwoliły na dobrą kontrolę wysiłku.",
  },
];

const weeklyBars = [48, 66, 52, 78, 62, 87, 74, 91, 68, 80, 72, 96];

export default function App() {
  const [page, setPage] = useState<Page>("dashboard");
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  function sync() {
    setIsSyncing(true);
    window.setTimeout(() => {
      setIsSyncing(false);
      setToast("Demo: synchronizacja zostanie połączona z Garminem po konfiguracji backendu.");
      window.setTimeout(() => setToast(null), 4500);
    }, 900);
  }

  function goTo(nextPage: Page) {
    setPage(nextPage);
    if (nextPage !== "runs") setSelectedRun(null);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-mark"><Activity size={18} strokeWidth={2.7} /></div>
        <div className="brand-copy">
          <span className="brand-name">Running Coach</span>
          <span className="brand-subtitle">Twój trener w danych</span>
        </div>
        <nav className="side-nav" aria-label="Główna nawigacja">
          <NavButton active={page === "dashboard"} icon={<LayoutDashboard size={18} />} label="Panel" onClick={() => goTo("dashboard")} />
          <NavButton active={page === "runs"} icon={<CalendarDays size={18} />} label="Treningi" onClick={() => goTo("runs")} />
          <NavButton active={page === "chat"} icon={<MessageCircle size={18} />} label="Trener AI" onClick={() => goTo("chat")} />
          <NavButton active={page === "settings"} icon={<Settings size={18} />} label="Ustawienia" onClick={() => goTo("settings")} />
        </nav>
        <div className="sidebar-footer">
          <div className="avatar">P</div>
          <div><strong>Patrycja</strong><span>Tryb demonstracyjny</span></div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <div className="eyebrow">RUNNING COACH <span className="demo-pill">DEMO</span></div>
            <h1>{page === "dashboard" ? "Dzień dobry, Patrycja" : page === "runs" ? "Twoje treningi" : page === "chat" ? "Porozmawiaj z trenerem" : "Ustawienia"}</h1>
          </div>
          <div className="topbar-actions">
            <span className="last-sync"><span className="status-dot" />Dane z 22 lis, 08:40</span>
            <button className="sync-button" onClick={sync} disabled={isSyncing}>
              <RefreshCw size={15} className={isSyncing ? "spin" : ""} />
              {isSyncing ? "Aktualizuję…" : "Aktualizuj"}
            </button>
          </div>
        </header>

        {page === "dashboard" && <Dashboard onOpenRun={(run) => { setSelectedRun(run); setPage("runs"); }} onOpenChat={() => goTo("chat")} />}
        {page === "runs" && <RunsPage selectedRun={selectedRun} onSelect={setSelectedRun} />}
        {page === "chat" && <ChatPage />}
        {page === "settings" && <SettingsPage />}
      </main>

      <nav className="mobile-nav" aria-label="Nawigacja mobilna">
        <NavButton active={page === "dashboard"} icon={<LayoutDashboard size={20} />} label="Panel" onClick={() => goTo("dashboard")} />
        <NavButton active={page === "runs"} icon={<CalendarDays size={20} />} label="Treningi" onClick={() => goTo("runs")} />
        <NavButton active={page === "chat"} icon={<MessageCircle size={20} />} label="Trener" onClick={() => goTo("chat")} />
        <NavButton active={page === "settings"} icon={<Settings size={20} />} label="Ustawienia" onClick={() => goTo("settings")} />
      </nav>

      {toast && <div className="toast"><CircleHelp size={17} />{toast}<button onClick={() => setToast(null)} aria-label="Zamknij"><X size={15} /></button></div>}
    </div>
  );
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: ReactNode; label: string; onClick: () => void }) {
  return <button className={`nav-button ${active ? "active" : ""}`} onClick={onClick}>{icon}<span>{label}</span></button>;
}

function Dashboard({ onOpenRun, onOpenChat }: { onOpenRun: (run: Run) => void; onOpenChat: () => void }) {
  return (
    <div className="page-stack">
      <section className="hero-card">
        <div className="hero-copy">
          <div className="eyebrow pale">TWOJA FORMA · OSTATNIE 28 DNI</div>
          <h2>Masz dobry sygnał szybkości.<br /><em>Teraz budujemy wytrzymałość.</em></h2>
          <p>Benchmark z 22 listopada był mocny. Kolejny krok to spokojna, regularna objętość — bez pogoni za tempem na każdym treningu.</p>
          <button className="light-button" onClick={onOpenChat}>Zapytaj trenera <ChevronRight size={16} /></button>
        </div>
        <div className="hero-score">
          <div className="score-ring"><span>78</span><small>/ 100</small></div>
          <span>Ocena gotowości</span>
          <strong>Stabilnie</strong>
        </div>
      </section>

      <section className="metric-grid">
        <MetricCard icon={<Trophy size={17} />} label="Najlepszy sygnał" value="4:57" unit="/km" caption="Benchmark 5 min" tone="green" />
        <MetricCard icon={<Activity size={17} />} label="Bieganie w tygodniu" value="18,3" unit="km" caption="+12% vs poprzedni" tone="blue" />
        <MetricCard icon={<HeartPulse size={17} />} label="Śr. tętno easy" value="143" unit="bpm" caption="W Twojej bazie" tone="orange" />
        <MetricCard icon={<TrendingUp size={17} />} label="Regularność" value="3 / 4" unit="biegów" caption="Cel tygodnia" tone="purple" />
      </section>

      <div className="content-grid">
        <section className="card chart-card">
          <div className="section-heading"><div><div className="eyebrow">OBCIĄŻENIE BIEGOWE</div><h2>Objętość z ostatnich tygodni</h2></div><span className="select-chip">12 tygodni <ChevronRight size={14} /></span></div>
          <div className="chart-summary"><strong>52,7 km</strong><span><span className="trend-up">↗ 8,4%</span> vs poprzednie 12 tyg.</span></div>
          <div className="bar-chart" aria-label="Wykres objętości biegowej">{weeklyBars.map((height, index) => <div className="bar-column" key={index}><div className={`bar ${index === weeklyBars.length - 1 ? "current" : ""}`} style={{ height: `${height}%` }} /><span>{index % 3 === 0 ? `T${index + 1}` : ""}</span></div>)}</div>
          <div className="chart-legend"><span><i className="legend-dot green" />Kilometry biegowe</span><span><i className="legend-line" />Trend regularności</span></div>
        </section>
        <section className="card recommendation-card">
          <div className="section-heading"><div><div className="eyebrow">REKOMENDACJA NA DZIŚ</div><h2>Co teraz?</h2></div><Sparkles size={20} className="sparkle" /></div>
          <div className="recommendation-icon"><CloudSun size={25} /></div>
          <h3>Trzymaj spokojny plan</h3>
          <p>Po wczorajszym teście daj układowi nerwowemu dzień bez intensywności. Lekki bieg lub odpoczynek będą lepszym bodźcem niż kolejny szybki trening.</p>
          <div className="recommendation-proof"><Check size={15} /> Rekomendacja oparta na 10 ostatnich aktywnościach</div>
          <button className="text-button" onClick={onOpenChat}>Zobacz uzasadnienie <ChevronRight size={15} /></button>
        </section>
      </div>

      <section className="card recent-card">
        <div className="section-heading"><div><div className="eyebrow">OSTATNIE TRENINGI</div><h2>Co wydarzyło się ostatnio</h2></div><button className="text-button" onClick={() => onOpenRun(runs[0])}>Wszystkie treningi <ChevronRight size={15} /></button></div>
        <div className="run-list">{runs.map((run) => <RunRow key={run.id} run={run} onClick={() => onOpenRun(run)} />)}</div>
      </section>
    </div>
  );
}

function MetricCard({ icon, label, value, unit, caption, tone }: { icon: ReactNode; label: string; value: string; unit: string; caption: string; tone: string }) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}>{icon}</div><div className="metric-label">{label}</div><div className="metric-value">{value}<span>{unit}</span></div><div className="metric-caption">{caption}</div></article>;
}

function RunRow({ run, onClick }: { run: Run; onClick: () => void }) {
  const statusLabel = run.status === "above" ? "Powyżej oczekiwań" : run.status === "steady" ? "Stabilnie" : "Lekko";
  return <button className="run-row" onClick={onClick}><div className="run-date"><span className="run-day">{run.date.split(" ")[0]}</span><span>{run.date.split(" ").slice(1).join(" ")}</span></div><div className="run-main"><strong>{run.title}</strong><span>{run.type}</span></div><div className="run-stat"><span>Dystans</span><strong>{run.distance}</strong></div><div className="run-stat"><span>Tempo</span><strong>{run.pace}<small>/km</small></strong></div><div className={`status-tag ${run.status}`}>{statusLabel}</div><ChevronRight size={17} className="row-arrow" /></button>;
}

function RunsPage({ selectedRun, onSelect }: { selectedRun: Run | null; onSelect: (run: Run | null) => void }) {
  if (selectedRun) return <RunDetail run={selectedRun} onBack={() => onSelect(null)} />;
  return <div className="page-stack"><div className="page-intro"><div><p>Historia od 1 stycznia 2025</p><h2>Wszystkie aktywności</h2></div><div className="filter-row"><button className="filter active">Wszystkie</button><button className="filter">Bieganie</button><button className="filter">Ostatnie 30 dni</button></div></div><section className="card runs-page-card"><div className="run-list">{runs.map((run) => <RunRow key={run.id} run={run} onClick={() => onSelect(run)} />)}</div><div className="empty-more">Kolejne aktywności pojawią się po synchronizacji z Garmin Connect.</div></section></div>;
}

function RunDetail({ run, onBack }: { run: Run; onBack: () => void }) {
  return <div className="page-stack"><button className="back-button" onClick={onBack}>← Wróć do treningów</button><section className="detail-head"><div><div className="eyebrow">{run.date} · {run.type.toUpperCase()}</div><h2>{run.title}</h2><p>Demo — szczegóły zostaną zasilone danymi z Garmin Connect.</p></div><div className={`status-tag ${run.status}`}>{run.status === "above" ? "Powyżej oczekiwań" : "Stabilnie"}</div></section><section className="metric-grid detail-metrics"><MetricCard icon={<Activity size={17} />} label="Dystans" value={run.distance.replace(" km", "")} unit=" km" caption="Cała sesja" tone="green" /><MetricCard icon={<Timer size={17} />} label="Tempo" value={run.pace} unit="/km" caption="Średnie z sesji" tone="blue" /><MetricCard icon={<HeartPulse size={17} />} label="Średnie tętno" value={run.heartRate} unit=" bpm" caption="Dane z zegarka" tone="orange" /><MetricCard icon={<Clock3 size={17} />} label="Czas" value={run.duration} unit="" caption="Czas ruchu" tone="purple" /></section><section className="content-grid"><article className="card analysis-card"><div className="eyebrow">ANALIZA AI</div><h2>{run.description}</h2><div className="evidence"><Check size={15} /> Analiza bez założeń planu treningowego</div></article><article className="card note-card"><div className="eyebrow">UZUPEŁNIJ TRENING</div><h2>Jak Ci się biegło?</h2><textarea placeholder="Opcjonalna notatka, odczuwalna trudność, ból…" /><button className="primary-button">Zapisz notatkę</button><small>Demo: zapis do prywatnego repozytorium zostanie podłączony w kolejnym etapie.</small></article></section></div>;
}

function ChatPage() {
  const [message, setMessage] = useState("");
  const [sent, setSent] = useState<string[]>([]);
  function send() { if (!message.trim()) return; setSent([...sent, message.trim()]); setMessage(""); }
  return <div className="chat-layout"><section className="card chat-card"><div className="chat-header"><div className="coach-avatar"><Sparkles size={20} /></div><div><div className="eyebrow">TRENER AI · DEMO</div><h2>Jestem przy Twoich danych</h2></div><span className="online-dot">gotowy</span></div><div className="chat-messages"><div className="chat-bubble coach"><strong>Running Coach</strong><p>Zapytaj mnie o ostatni trening, progres, regenerację albo o to, jak rozumieć dane z Garmina.</p></div>{sent.map((item, index) => <div className="chat-bubble user" key={`${item}-${index}`}>{item}</div>)}{sent.length > 0 && <div className="chat-bubble coach"><strong>Running Coach</strong><p>W trybie demo nie mam jeszcze dostępu do prawdziwej historii. Po konfiguracji backendu będę odpowiadać na podstawie Twoich aktywności.</p></div>}</div><div className="suggestions"><button onClick={() => setMessage("Jak wygląda mój progres w ostatnich 4 tygodniach?")}>Jak wygląda mój progres?</button><button onClick={() => setMessage("Co zrobić na następnym treningu?")}>Co na następnym treningu?</button></div><div className="chat-input"><input value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") send(); }} placeholder="Napisz do trenera…" /><button onClick={send} aria-label="Wyślij"><ChevronRight size={19} /></button></div></section><aside className="card chat-side"><div className="eyebrow">PAMIĘĆ TRENERA</div><h2>Co wiem o Twoim bieganiu</h2><ul><li><Check size={15} /> Cel: półmaraton w marcu 2027</li><li><Check size={15} /> Preferujesz 3–4 biegi tygodniowo</li><li><Check size={15} /> Garmin Coach prowadzi plan</li></ul><div className="notice-box"><CircleHelp size={17} /><span>Pamięć jest jawna i będzie zapisywana w prywatnym repozytorium danych.</span></div></aside></div>;
}

function SettingsPage() {
  return <div className="settings-grid"><section className="card settings-card"><div className="eyebrow">POŁĄCZENIE</div><h2>Źródła danych</h2><div className="connection-row"><div className="connection-logo garmin">G</div><div><strong>Garmin Connect Personal API</strong><span>Jeszcze nie skonfigurowano</span></div><span className="connection-status pending">Do ustawienia</span></div><p className="settings-help">Klucz Garmina dodasz w środowisku backendu, nie w kodzie aplikacji. Otrzymasz instrukcję przed pierwszą synchronizacją.</p></section><section className="card settings-card"><div className="eyebrow">PROFIL</div><h2>Twoje założenia</h2><label>Cel główny<input value="Półmaraton · marzec 2027" readOnly /></label><label>Liczba biegów w tygodniu<input value="3–4" readOnly /></label><label>Strefa czasowa<input value="Europe/Warsaw" readOnly /></label><button className="primary-button">Edytuj profil</button></section><section className="card settings-card wide"><div className="eyebrow">PRYWATNOŚĆ</div><h2>Twoje dane pozostają pod kontrolą</h2><div className="privacy-list"><span><Check size={15} /> Repozytorium danych jest prywatne</span><span><Check size={15} /> GPS zostanie usunięty przed analizą</span><span><Check size={15} /> Klucze API nie trafiają do frontendu</span></div></section></div>;
}

