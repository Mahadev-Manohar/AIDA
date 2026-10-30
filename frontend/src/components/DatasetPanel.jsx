import { useMemo, useState } from 'react';
import Icon from './Icon';
import { MAX_UPLOAD_MB } from '../config';
import { dtypeKind } from '../utils';

const KIND_LABEL = { num: 'numeric', bool: 'boolean', date: 'datetime', text: 'text' };

export default function DatasetPanel({ dataset, uploadProgress, onPickFile, onFile, onClear }) {
  const [dragActive, setDragActive] = useState(false);
  const [query, setQuery] = useState('');
  const uploading = uploadProgress !== null;

  const counts = useMemo(() => {
    const c = { num: 0, text: 0, bool: 0, date: 0 };
    if (dataset) dataset.columns.forEach((col) => c[dtypeKind(dataset.dtypes?.[col])]++);
    return c;
  }, [dataset]);

  const filtered = useMemo(() => {
    if (!dataset) return [];
    const q = query.trim().toLowerCase();
    return q ? dataset.columns.filter((c) => c.toLowerCase().includes(q)) : dataset.columns;
  }, [dataset, query]);

  const handleDrag = (e) => {
    e.preventDefault();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  };

  return (
    <div className="panel-body">
      <div className="panel-title">
        <Icon name="database" size={15} /> Dataset
      </div>

      {uploading ? (
        <div className="card upload-progress">
          <div className="muted small">Uploading…</div>
          <div className="progress">
            <div className="progress-bar" style={{ width: `${Math.round(uploadProgress * 100)}%` }} />
          </div>
          <div className="small">{Math.round(uploadProgress * 100)}%</div>
        </div>
      ) : !dataset ? (
        <div
          className={`dropzone ${dragActive ? 'active' : ''}`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={onPickFile}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onPickFile()}
        >
          <div className="dropzone-icon">
            <Icon name="upload" size={22} />
          </div>
          <div className="dropzone-title">Drop a CSV here</div>
          <div className="muted small">
            or <span className="link">browse files</span> · up to {MAX_UPLOAD_MB}MB
          </div>
        </div>
      ) : (
        <>
          <div className="card file-card">
            <div className="file-icon">
              <Icon name="file" size={18} />
            </div>
            <div className="file-details">
              <div className="file-name" title={dataset.filename}>
                {dataset.filename}
              </div>
              <div className="muted small">
                {dataset.shape.rows.toLocaleString()} rows · {dataset.shape.columns} columns
              </div>
            </div>
          </div>

          <div className="stat-grid">
            <div className="stat">
              <div className="stat-value">{counts.num}</div>
              <div className="stat-label">Numeric</div>
            </div>
            <div className="stat">
              <div className="stat-value">{counts.text + counts.bool + counts.date}</div>
              <div className="stat-label">Other</div>
            </div>
          </div>

          <div className="row-actions">
            <button type="button" className="btn btn-secondary" onClick={onPickFile}>
              <Icon name="upload" size={14} /> Replace
            </button>
            <button type="button" className="btn btn-danger-ghost" onClick={onClear}>
              <Icon name="trash" size={14} /> Clear
            </button>
          </div>

          <div className="panel-title section">
            Columns <span className="count-badge">{dataset.columns.length}</span>
          </div>
          <label className="search">
            <Icon name="search" size={14} />
            <input
              type="search"
              placeholder="Filter columns"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              aria-label="Filter columns"
            />
          </label>
          <ul className="column-list">
            {filtered.map((col) => {
              const kind = dtypeKind(dataset.dtypes?.[col]);
              return (
                <li key={col} className="column-item" title={`${col} (${dataset.dtypes?.[col] ?? 'unknown'})`}>
                  <span className="column-name">{col}</span>
                  <span className={`type-badge ${kind}`}>{KIND_LABEL[kind]}</span>
                </li>
              );
            })}
            {filtered.length === 0 && <li className="muted small empty-line">No matching columns</li>}
          </ul>
        </>
      )}
    </div>
  );
}
