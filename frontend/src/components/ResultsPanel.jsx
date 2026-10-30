import { useState } from 'react';
import Icon from './Icon';

export default function ResultsPanel({ plots, dataset, onOpenPlot }) {
  const [tab, setTab] = useState('charts');

  return (
    <div className="panel-body results">
      <div className="tabs" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'charts'}
          className={`tab ${tab === 'charts' ? 'active' : ''}`}
          onClick={() => setTab('charts')}
        >
          <Icon name="image" size={14} /> Charts
          {plots.length > 0 && <span className="count-badge">{plots.length}</span>}
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'data'}
          className={`tab ${tab === 'data' ? 'active' : ''}`}
          onClick={() => setTab('data')}
        >
          <Icon name="table" size={14} /> Data preview
        </button>
      </div>

      {tab === 'charts' ? (
        plots.length === 0 ? (
          <div className="empty-state">
            <Icon name="chart" size={26} />
            <div className="empty-title">No charts yet</div>
            <div className="muted small">
              Ask AIDA to plot a distribution, a relationship or a correlation heatmap and it will show up here.
            </div>
          </div>
        ) : (
          <div className="plot-grid">
            {plots.map((plot, idx) => (
              <button type="button" key={plot.plot_path} className="plot-card" onClick={() => onOpenPlot(idx)}>
                <div className="plot-thumb">
                  <img src={plot.url} alt={plot.summary} loading="lazy" />
                </div>
                <div className="plot-caption">{plot.summary}</div>
              </button>
            ))}
          </div>
        )
      ) : (
        <DataTable dataset={dataset} />
      )}
    </div>
  );
}

function DataTable({ dataset }) {
  if (!dataset?.data) {
    return (
      <div className="empty-state">
        <Icon name="table" size={26} />
        <div className="empty-title">No dataset loaded</div>
        <div className="muted small">Upload a CSV to preview its first rows.</div>
      </div>
    );
  }

  return (
    <>
      <div className="muted small table-note">
        Showing first {dataset.data.length} of {dataset.shape.rows.toLocaleString()} rows
      </div>
      <div className="data-table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              {dataset.columns.map((col) => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataset.data.map((row, r) => (
              <tr key={r}>
                {dataset.columns.map((col) => {
                  const v = row[col];
                  return v === null || v === undefined ? (
                    <td key={col} className="null-cell">
                      null
                    </td>
                  ) : (
                    <td key={col} className={typeof v === 'number' ? 'num-cell' : ''}>
                      {String(v)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
