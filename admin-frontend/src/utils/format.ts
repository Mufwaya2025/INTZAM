export function formatMoney(value: number | string | null | undefined, currency = 'ZMW') {
    const num = Number(value || 0);
    return `${currency} ${num.toLocaleString(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
    })}`;
}

export function formatMoneyAbs(value: number | string | null | undefined, currency = 'ZMW') {
    return formatMoney(Math.abs(Number(value || 0)), currency);
}
