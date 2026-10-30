import { resolveSrc } from '../utils';

const INLINE = /(`[^`\n]+`|\*\*[^*\n]+?\*\*|(?<![*\w])\*[^*\n]+?\*(?!\w)|\[[^\]]+\]\([^)\s]+\))/g;
const TABLE_SEP = /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/;
const UL = /^\s*[-*+]\s+/;
const OL = /^\s*\d+[.)]\s+/;
const IMAGE = /^!\[(.*?)\]\((\S+?)\)\s*$/;

function renderInline(text) {
  return text.split(INLINE).map((part, i) => {
    if (i % 2 === 0) return part;
    if (part.startsWith('`')) return <code key={i}>{part.slice(1, -1)}</code>;
    if (part.startsWith('**')) return <strong key={i}>{renderInline(part.slice(2, -2))}</strong>;
    if (part.startsWith('[')) {
      const m = part.match(/^\[(.+?)\]\((.+)\)$/);
      if (m && /^(https?:|\/)/.test(m[2])) {
        return (
          <a key={i} href={m[2]} target="_blank" rel="noreferrer">
            {m[1]}
          </a>
        );
      }
      return part;
    }
    return <em key={i}>{part.slice(1, -1)}</em>;
  });
}

function isBlockStart(line, next) {
  return (
    /^```/.test(line) ||
    /^#{1,4}\s/.test(line) ||
    IMAGE.test(line) ||
    UL.test(line) ||
    OL.test(line) ||
    /^\s*>/.test(line) ||
    (line.includes('|') && next !== undefined && TABLE_SEP.test(next))
  );
}

function splitRow(row) {
  return row
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((c) => c.trim());
}

function parseBlocks(src) {
  const lines = src.replace(/\r\n/g, '\n').split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }

    let m = line.match(/^```(\w*)/);
    if (m) {
      const code = [];
      i++;
      while (i < lines.length && !/^```/.test(lines[i])) code.push(lines[i++]);
      i++; // closing fence
      blocks.push({ type: 'code', lang: m[1], text: code.join('\n') });
      continue;
    }

    m = line.match(/^(#{1,4})\s+(.*)$/);
    if (m) {
      blocks.push({ type: 'heading', level: m[1].length, text: m[2] });
      i++;
      continue;
    }

    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) {
      blocks.push({ type: 'hr' });
      i++;
      continue;
    }

    m = line.match(IMAGE);
    if (m) {
      blocks.push({ type: 'image', alt: m[1], src: m[2] });
      i++;
      continue;
    }

    if (/^\s*>/.test(line)) {
      const quote = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) quote.push(lines[i++].replace(/^\s*>\s?/, ''));
      blocks.push({ type: 'quote', text: quote.join('\n') });
      continue;
    }

    if (line.includes('|') && i + 1 < lines.length && TABLE_SEP.test(lines[i + 1])) {
      const header = splitRow(line);
      const aligns = splitRow(lines[i + 1]).map((c) =>
        c.startsWith(':') && c.endsWith(':') ? 'center' : c.endsWith(':') ? 'right' : 'left',
      );
      const rows = [];
      i += 2;
      while (i < lines.length && lines[i].trim() && lines[i].includes('|')) rows.push(splitRow(lines[i++]));
      blocks.push({ type: 'table', header, aligns, rows });
      continue;
    }

    if (UL.test(line) || OL.test(line)) {
      const ordered = OL.test(line);
      const re = ordered ? OL : UL;
      const items = [];
      while (i < lines.length && re.test(lines[i])) items.push(lines[i++].replace(re, ''));
      blocks.push({ type: 'list', ordered, items });
      continue;
    }

    const para = [line];
    i++;
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i], lines[i + 1])) para.push(lines[i++]);
    blocks.push({ type: 'paragraph', lines: para });
  }

  return blocks;
}

export default function Markdown({ text, onImageClick }) {
  if (!text) return null;

  return (
    <div className="markdown">
      {parseBlocks(text).map((b, i) => {
        switch (b.type) {
          case 'heading': {
            const Tag = `h${Math.min(b.level + 1, 5)}`;
            return <Tag key={i}>{renderInline(b.text)}</Tag>;
          }
          case 'code':
            return (
              <pre key={i} className="md-code">
                <code>{b.text}</code>
              </pre>
            );
          case 'hr':
            return <hr key={i} />;
          case 'quote':
            return <blockquote key={i}>{renderInline(b.text)}</blockquote>;
          case 'image':
            return (
              <figure key={i} className="md-figure">
                <img
                  src={resolveSrc(b.src)}
                  alt={b.alt}
                  loading="lazy"
                  onClick={() => onImageClick?.({ plot_path: b.src, summary: b.alt })}
                />
                {b.alt && <figcaption>{b.alt}</figcaption>}
              </figure>
            );
          case 'table':
            return (
              <div key={i} className="md-table-wrap">
                <table>
                  <thead>
                    <tr>
                      {b.header.map((h, c) => (
                        <th key={c} style={{ textAlign: b.aligns[c] }}>
                          {renderInline(h)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {b.rows.map((row, r) => (
                      <tr key={r}>
                        {b.header.map((_, c) => (
                          <td key={c} style={{ textAlign: b.aligns[c] }}>
                            {renderInline(row[c] ?? '')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          case 'list': {
            const Tag = b.ordered ? 'ol' : 'ul';
            return (
              <Tag key={i}>
                {b.items.map((item, k) => (
                  <li key={k}>{renderInline(item)}</li>
                ))}
              </Tag>
            );
          }
          default:
            return (
              <p key={i}>
                {b.lines.map((l, k) => (
                  <span key={k}>
                    {renderInline(l)}
                    {k < b.lines.length - 1 && <br />}
                  </span>
                ))}
              </p>
            );
        }
      })}
    </div>
  );
}
