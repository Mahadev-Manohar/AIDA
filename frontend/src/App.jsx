import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import './App.css';
import { clearDataset, fetchConfig, fetchDataset, plotUrl, streamQuery, uploadCsv } from './api';
import { MAX_UPLOAD_MB } from './config';
import { useTheme } from './hooks/useTheme';
import Header from './components/Header';
import { dtypeKind } from './utils';
import DatasetPanel from './components/DatasetPanel';
import ChatPanel from './components/ChatPanel';
import ResultsPanel from './components/ResultsPanel';
import PlotModal from './components/PlotModal';
import Toasts from './components/Toasts';
import Icon from './components/Icon';

const TARGET_HINT = /target|label|class|outcome|default|dlq|churn|survived|price|status/i;

const ID_LIKE = /^(unnamed.*|id|index)$/i;

function buildSuggestions(dataset) {
  if (!dataset) return [];
  const numeric = dataset.columns.find(
    (c) => dtypeKind(dataset.dtypes?.[c]) === 'num' && !ID_LIKE.test(c) && !TARGET_HINT.test(c),
  );
  const target = dataset.columns.find((c) => TARGET_HINT.test(c)) ?? dataset.columns[dataset.columns.length - 1];
  const list = ['Give me an overview of this dataset and its data quality'];
  if (numeric) list.push(`Plot the distribution of ${numeric}`);
  list.push('Show a correlation heatmap of the numeric columns');
  if (target) list.push(`Train a baseline model to predict ${target}`);
  return list;
}

let idCounter = 0;
const nextId = (prefix) => `${prefix}-${Date.now()}-${idCounter++}`;

export default function App() {
  const [theme, toggleTheme] = useTheme();

  const [backend, setBackend] = useState({ status: 'checking', model: '' });
  const [dataset, setDataset] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(null);

  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [plots, setPlots] = useState([]);
  const [modalIndex, setModalIndex] = useState(null);

  const [toasts, setToasts] = useState([]);
  const [mobileTab, setMobileTab] = useState('chat');

  const fileInputRef = useRef(null);
  const abortRef = useRef(null);

  const notify = useCallback((message, tone = 'info') => {
    const id = nextId('toast');
    setToasts((prev) => [...prev, { id, message, tone }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 5000);
  }, []);

  const dismissToast = useCallback((id) => setToasts((prev) => prev.filter((t) => t.id !== id)), []);

  const loadBackendState = useCallback(async () => {
    setBackend((b) => ({ ...b, status: 'checking' }));
    try {
      const cfg = await fetchConfig();
      setBackend({ status: cfg.api_key_configured ? 'ready' : 'nokey', model: cfg.model });
      const ds = await fetchDataset();
      setDataset(ds.loaded ? ds : null);
    } catch {
      setBackend({ status: 'offline', model: '' });
    }
  }, []);

  useEffect(() => {
    loadBackendState();
  }, [loadBackendState]);

  const suggestions = useMemo(() => buildSuggestions(dataset), [dataset]);

  const addNotice = (text) => setMessages((prev) => [...prev, { id: nextId('notice'), role: 'notice', text }]);

  // ---- Dataset handling ----
  const handleFile = useCallback(
    async (file) => {
      if (!file.name.toLowerCase().endsWith('.csv')) {
        notify('Only .csv files are supported.', 'error');
        return;
      }
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        notify(`File is larger than ${MAX_UPLOAD_MB}MB.`, 'error');
        return;
      }
      setUploadProgress(0);
      try {
        const data = await uploadCsv(file, setUploadProgress);
        const preview = await fetchDataset();
        setDataset(preview.loaded ? preview : null);
        setPlots([]);
        setMobileTab('chat');
        setMessages((prev) =>
          prev.length === 0
            ? prev
            : [...prev, { id: nextId('notice'), role: 'notice', text: `Loaded new dataset: ${data.filename}` }],
        );
        notify(
          `Loaded ${data.filename} (${data.shape.rows.toLocaleString()} rows × ${data.shape.columns} columns)`,
          'success',
        );
      } catch (err) {
        notify(err.message, 'error');
      } finally {
        setUploadProgress(null);
      }
    },
    [notify],
  );

  const pickFile = useCallback(() => fileInputRef.current?.click(), []);

  const handleClear = async () => {
    try {
      await clearDataset();
      setDataset(null);
      setPlots([]);
      if (messages.length > 0) addNotice('Dataset cleared');
    } catch (err) {
      notify(err.message, 'error');
    }
  };

  // ---- Chat ----
  const patchMessage = (id, fn) => setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));

  const registerPlot = (path, summary) => {
    const plot = { plot_path: path, summary, url: plotUrl(path) };
    setPlots((prev) => {
      const i = prev.findIndex((p) => p.plot_path === path);
      if (i === -1) return [...prev, plot];
      const copy = [...prev];
      copy[i] = plot;
      return copy;
    });
  };

  const handleSend = useCallback(
    async (query) => {
      if (loading) return;
      const agentId = nextId('agent');
      setMessages((prev) => [
        ...prev,
        { id: nextId('user'), role: 'user', text: query },
        { id: agentId, role: 'agent', text: '', steps: [], status: 'streaming', activity: 'Starting…' },
      ]);
      setLoading(true);
      setMobileTab('chat');

      const controller = new AbortController();
      abortRef.current = controller;
      const addStep = (step, extra = {}) =>
        patchMessage(agentId, (m) => ({ ...m, steps: [...m.steps, step], ...extra }));

      try {
        for await (const step of streamQuery(query, controller.signal)) {
          switch (step.type) {
            case 'info':
              patchMessage(agentId, (m) => ({ ...m, activity: step.content }));
              break;
            case 'thought':
              addStep({ type: 'thought', content: step.content }, { activity: 'Reasoning…' });
              break;
            case 'tool_call':
              addStep({ type: 'tool_call', name: step.name, arguments: step.arguments }, { activity: `Running ${step.name}…` });
              break;
            case 'tool_output':
              addStep({ type: 'tool_output', name: step.name, result: step.result }, { activity: 'Analyzing result…' });
              if (step.result?.plot_path) {
                registerPlot(step.result.plot_path, step.result.summary || step.result.message || step.name);
              }
              break;
            case 'error':
              addStep({ type: 'error', content: step.content });
              patchMessage(agentId, (m) => ({
                ...m,
                status: 'error',
                text: m.text || step.content || 'An error occurred during agent reasoning.',
              }));
              break;
            case 'final_answer':
              patchMessage(agentId, (m) => ({ ...m, text: step.content, status: 'done', activity: '' }));
              break;
            default:
              break;
          }
        }
        patchMessage(agentId, (m) => (m.status === 'streaming' ? { ...m, status: 'done', activity: '' } : m));
      } catch (err) {
        if (err.name === 'AbortError') {
          patchMessage(agentId, (m) => ({ ...m, status: 'done', activity: '', text: m.text || '*Stopped.*' }));
        } else {
          patchMessage(agentId, (m) => ({
            ...m,
            status: 'error',
            activity: '',
            text: `Failed to run the agent: **${err.message}**. Make sure the FastAPI backend is running and your API key is set.`,
          }));
        }
      } finally {
        abortRef.current = null;
        setLoading(false);
      }
    },
    [loading],
  );

  const handleStop = useCallback(() => abortRef.current?.abort(), []);

  const handleNewChat = () => {
    abortRef.current?.abort();
    setMessages([]);
  };

  // ---- Plot modal ----
  const openPlotByPath = ({ plot_path, summary }) => {
    const existing = plots.findIndex((p) => p.plot_path === plot_path);
    if (existing !== -1) {
      setModalIndex(existing);
      return;
    }
    registerPlot(plot_path, summary || 'Generated chart');
    setModalIndex(plots.length);
  };

  const closeModal = useCallback(() => setModalIndex(null), []);

  // Stop the browser from navigating to a file dropped outside the dropzone
  const ignoreDrop = (e) => e.preventDefault();

  return (
    <div className="app" onDragOver={ignoreDrop} onDrop={ignoreDrop}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,text/csv"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = '';
          if (file) handleFile(file);
        }}
      />

      <Header
        status={backend.status}
        model={backend.model}
        theme={theme}
        onToggleTheme={toggleTheme}
        onRetry={loadBackendState}
        onNewChat={handleNewChat}
        canReset={messages.length > 0}
      />

      <main className="layout" data-tab={mobileTab}>
        <aside className="panel panel-left">
          <DatasetPanel
            dataset={dataset}
            uploadProgress={uploadProgress}
            onPickFile={pickFile}
            onFile={handleFile}
            onClear={handleClear}
          />
        </aside>

        <section className="panel panel-center">
          <ChatPanel
            messages={messages}
            loading={loading}
            dataset={dataset}
            suggestions={suggestions}
            onSend={handleSend}
            onStop={handleStop}
            onPickFile={pickFile}
            onImageClick={openPlotByPath}
          />
        </section>

        <aside className="panel panel-right">
          <ResultsPanel plots={plots} dataset={dataset} onOpenPlot={setModalIndex} />
        </aside>
      </main>

      <nav className="mobile-nav" aria-label="Sections">
        {[
          ['data', 'Dataset', 'database'],
          ['chat', 'Chat', 'chat'],
          ['results', 'Results', 'chart'],
        ].map(([key, label, icon]) => (
          <button
            type="button"
            key={key}
            className={mobileTab === key ? 'active' : ''}
            onClick={() => setMobileTab(key)}
          >
            <Icon name={icon} size={18} />
            {label}
          </button>
        ))}
      </nav>

      {modalIndex !== null && (
        <PlotModal plots={plots} index={modalIndex} onClose={closeModal} onNavigate={setModalIndex} />
      )}

      <Toasts toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
