/** Format numbers with the currency from the bootstrap payload (settings.currency*). */

let SYMBOL = '';

export function setCurrency(symbol) {
  if (symbol) SYMBOL = symbol;
}

export function currencySymbol() {
  return SYMBOL;
}

/**
 * Format money consistently.
 *   formatMoney(1755000)                    → "₦1,755,000"
 *   formatMoney(1755000, { compact: true }) → "₦1.8M"
 */
export function formatMoney(n, { compact = false } = {}) {
  if (n == null || Number.isNaN(Number(n))) return `${SYMBOL}—`;

  const num = Number(n);

  if (compact) {
    const abs = Math.abs(num);
    if (abs >= 1e9) return `${SYMBOL}${(num / 1e9).toFixed(1)}B`;
    if (abs >= 1e6) return `${SYMBOL}${(num / 1e6).toFixed(1)}M`;
    if (abs >= 1e3) return `${SYMBOL}${(num / 1e3).toFixed(1)}K`;
    return `${SYMBOL}${num.toFixed(0)}`;
  }

  return `${SYMBOL}${num.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}
