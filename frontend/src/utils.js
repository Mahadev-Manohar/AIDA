import { API_BASE } from './config';

export function dtypeKind(dtype = '') {
  if (/int|float|number/.test(dtype)) return 'num';
  if (/bool/.test(dtype)) return 'bool';
  if (/date|time/.test(dtype)) return 'date';
  return 'text';
}

export function resolveSrc(src) {
  return /^https?:/.test(src) ? src : `${API_BASE}${src}`;
}
