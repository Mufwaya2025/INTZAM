import React, { useState } from 'react';
import { reportsAPI } from '../services/api';
import { formatMoney } from '../utils/format';

interface ReportsPageProps {
    userPermissions: string[];
}

const REPORTS = [
    { id: 'disbursement-register', label: 'Disbursement Register', icon: '📋', category: 'Operations', desc: 'All disbursed loans with terms' },
    { id: 'active-loan-portfolio', label: 'Active Loan Portfolio', icon: '💼', category: 'Operations', desc: 'Current active loan summary' },
    { id: 'aging-par-report', label: 'Aging PAR Report', icon: '⚠️', category: 'Risk', desc: 'Portfolio at risk by aging bucket' },
    { id: 'daily-recovery-manifest', label: 'Daily Recovery Manifest', icon: '📞', category: 'Collections', desc: 'Overdue loans for collection' },
    { id: 'expected-collection', label: 'Expected Collection', icon: '📅', category: 'Collections', desc: 'Loans maturing in next 30 days' },
    { id: 'ptp-performance', label: 'PTP Performance', icon: '🤝', category: 'Collections', desc: 'Promise-to-pay fulfillment rates' },
    { id: 'income-statement', label: 'Income Statement', icon: '💰', category: 'Finance', desc: 'Monthly income and expenses' },
    { id: 'daily-cash-flow', label: 'Daily Cash Flow', icon: '💸', category: 'Finance', desc: 'Today\'s inflows and outflows' },
    { id: 'master-loan-tape', label: 'Master Loan Tape', icon: '🗂️', category: 'Compliance', desc: 'Complete loan data export' },
    { id: 'vintage-analysis', label: 'Vintage Analysis', icon: '📊', category: 'Analytics', desc: 'Loan cohort performance' },
    { id: 'ifrs9-expected-loss', label: 'IFRS 9 Expected Loss', icon: '📉', category: 'Compliance', desc: 'ECL calculation by stage' },
    { id: 'write-off-register', label: 'Write-off Register', icon: '❌', category: 'Risk', desc: 'Written-off loans history' },
];


export default function ReportsPage({ userPermissions }: ReportsPageProps) {
    const [selectedReport, setSelectedReport] = useState<string | null>(null);
    const [reportData, setReportData] = useState<any>(null);
    const [loading, setLoading] = useState(false);
    const [categoryFilter, setCategoryFilter] = useState('All');
    const [ecWindowDays, setEcWindowDays] = useState(30);
    const [vaProduct, setVaProduct] = useState('');

    const allowedReports = REPORTS.filter(r => userPermissions.includes(`report:${r.id}`));
    const visibleCategories = ['All', ...Array.from(new Set(allowedReports.map(r => r.category)))];

    const runReport = async (reportId: string, params?: Record<string, any>) => {
        setSelectedReport(reportId);
        setLoading(true);
        setReportData(null);
        try {
            const res = await reportsAPI.get(reportId, params);
            setReportData(res.data);
        } catch {
            setReportData(getMockReportData(reportId));
        } finally {
            setLoading(false);
        }
    };

    const rerunVintageAnalysis = async (product: string) => {
        setVaProduct(product);
        setLoading(true);
        setReportData(null);
        try {
            const params: Record<string, any> = {};
            if (product) params.product = product;
            const res = await reportsAPI.get('vintage-analysis', params);
            setReportData(res.data);
        } catch {
            setReportData(getMockReportData('vintage-analysis'));
        } finally {
            setLoading(false);
        }
    };

    const rerunExpectedCollection = async (days: number) => {
        setEcWindowDays(days);
        setLoading(true);
        setReportData(null);
        try {
            const res = await reportsAPI.get('expected-collection', { days });
            setReportData(res.data);
        } catch {
            setReportData(getMockReportData('expected-collection'));
        } finally {
            setLoading(false);
        }
    };

    const filtered = categoryFilter === 'All' ? allowedReports : allowedReports.filter(r => r.category === categoryFilter);

    const categoryColors: Record<string, string> = {
        Operations: 'badge-purple',
        Risk: 'badge-error',
        Collections: 'badge-warning',
        Finance: 'badge-success',
        Analytics: 'badge-info',
        Compliance: 'badge-gray',
    };

    return (
        <div style={{ display: 'grid', gridTemplateColumns: selectedReport ? '320px 1fr' : '1fr', gap: 20 }}>
            {/* Report Selector */}
            <div>
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Reports Center</h3>
                    </div>
                    <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--gray-100)' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {visibleCategories.map(cat => (
                                <button
                                    key={cat}
                                    className={`btn btn-sm ${categoryFilter === cat ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setCategoryFilter(cat)}
                                >
                                    {cat}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div style={{ padding: 12 }}>
                        {filtered.map(report => (
                            <div
                                key={report.id}
                                onClick={() => runReport(report.id)}
                                style={{
                                    padding: '12px 14px',
                                    borderRadius: 10,
                                    cursor: 'pointer',
                                    marginBottom: 4,
                                    background: selectedReport === report.id ? 'var(--primary-50)' : 'transparent',
                                    border: selectedReport === report.id ? '1.5px solid var(--primary-200)' : '1.5px solid transparent',
                                    transition: 'all 0.2s',
                                }}
                                onMouseEnter={e => { if (selectedReport !== report.id) e.currentTarget.style.background = 'var(--gray-50)'; }}
                                onMouseLeave={e => { if (selectedReport !== report.id) e.currentTarget.style.background = 'transparent'; }}
                            >
                                <div className="flex items-center gap-2 mb-2">
                                    <span style={{ fontSize: 18 }}>{report.icon}</span>
                                    <span style={{ fontWeight: 600, fontSize: 14 }}>{report.label}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className={`badge ${categoryColors[report.category]}`}>{report.category}</span>
                                    <span style={{ fontSize: 12, color: 'var(--gray-400)' }}>{report.desc}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Report Output */}
            {selectedReport && (
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">
                            {REPORTS.find(r => r.id === selectedReport)?.icon} {REPORTS.find(r => r.id === selectedReport)?.label}
                        </h3>
                        <div className="flex gap-2">
                            <span className="badge badge-gray">{reportData?.generated_at || 'Today'}</span>
                            <button className="btn btn-secondary btn-sm" onClick={() => { setSelectedReport(null); setReportData(null); }}>✕</button>
                        </div>
                    </div>
                    <div className="card-body">
                        {loading ? (
                            <div className="loading-overlay"><div className="loading-spinner" style={{ width: 32, height: 32 }}></div></div>
                        ) : reportData ? (
                            <ReportOutput data={reportData} reportId={selectedReport!} ecWindowDays={ecWindowDays} onEcWindowChange={rerunExpectedCollection} vaProduct={vaProduct} onVaProductChange={rerunVintageAnalysis} />
                        ) : null}
                    </div>
                </div>
            )}
        </div>
    );
}

// ─── Disbursement Register ────────────────────────────────────────────────────

const DR_COLS: { key: string; label: string; fmt?: 'currency' | 'pct' | 'stage' | 'class' | 'par' | 'status' }[] = [
    { key: 'no',                  label: '#' },
    { key: 'loan_number',         label: 'Loan No.' },
    { key: 'client_name',         label: 'Client Name' },
    { key: 'client_nrc',          label: 'NRC / ID' },
    { key: 'client_phone',        label: 'Phone' },
    { key: 'loan_cycle',          label: 'Cycle' },
    { key: 'gender',              label: 'Gender' },
    { key: 'age_group',           label: 'Age Group' },
    { key: 'client_tier',         label: 'Tier' },
    { key: 'employment_status',   label: 'Employment' },
    { key: 'monthly_income',      label: 'Monthly Income', fmt: 'currency' },
    { key: 'product',             label: 'Product' },
    { key: 'interest_type',       label: 'Int. Type' },
    { key: 'repayment_frequency', label: 'Frequency' },
    { key: 'purpose',             label: 'Purpose' },
    { key: 'disbursed_amount',    label: 'Disbursed', fmt: 'currency' },
    { key: 'total_repayable',     label: 'Total Repayable', fmt: 'currency' },
    { key: 'expected_interest',   label: 'Expected Interest', fmt: 'currency' },
    { key: 'monthly_payment',     label: 'Installment', fmt: 'currency' },
    { key: 'term_months',         label: 'Term (mo.)' },
    { key: 'interest_rate',       label: 'Rate %', fmt: 'pct' },
    { key: 'dti_ratio',           label: 'DTI %', fmt: 'pct' },
    { key: 'disbursement_date',   label: 'Disbursed On' },
    { key: 'maturity_date',       label: 'Maturity' },
    { key: 'repaid_amount',       label: 'Repaid', fmt: 'currency' },
    { key: 'outstanding_balance', label: 'Outstanding', fmt: 'currency' },
    { key: 'days_overdue',        label: 'DPD' },
    { key: 'approved_by',         label: 'Approved By' },
    { key: 'rollover_count',      label: 'Rollovers' },
    { key: 'status',              label: 'Status', fmt: 'status' },
    { key: 'loan_classification', label: 'Classification', fmt: 'class' },
    { key: 'ifrs9_stage',         label: 'IFRS 9 Stage', fmt: 'stage' },
    { key: 'par_flag',            label: 'PAR >30', fmt: 'par' },
];

const STATUS_COLORS: Record<string, string> = {
    ACTIVE: '#16a34a', OVERDUE: '#dc2626', CLOSED: '#6b7280',
    WRITTEN_OFF: '#7c3aed', APPROVED: '#2563eb',
};
const CLASS_COLORS: Record<string, string> = {
    Pass: '#16a34a', Watch: '#d97706', Substandard: '#ea580c',
    Doubtful: '#dc2626', Loss: '#7f1d1d',
};

function exportCSV(data: any[], filename: string) {
    if (!data.length) return;
    const headers = DR_COLS.map(c => c.label);
    const rows = data.map(row =>
        DR_COLS.map(c => {
            const v = row[c.key];
            if (v === null || v === undefined) return '';
            if (typeof v === 'boolean') return v ? 'Yes' : 'No';
            return String(v);
        })
    );
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename; a.click();
    URL.revokeObjectURL(url);
}

function DisbursementRegisterTable({ data: report }: { data: any }) {
    const [statusFilter, setStatusFilter] = useState('ALL');
    const summary = report.summary || {};
    const allRows: any[] = report.data || [];
    const rows = statusFilter === 'ALL' ? allRows : allRows.filter((r: any) => r.status === statusFilter);

    const statuses = ['ALL', ...Array.from(new Set(allRows.map((r: any) => r.status))) as string[]];

    const renderCell = (col: typeof DR_COLS[0], val: any) => {
        if (val === null || val === undefined || val === '') return <span style={{ color: '#ccc' }}>—</span>;
        switch (col.fmt) {
            case 'currency': return formatMoney(val);
            case 'pct':      return val != null ? `${val}%` : '—';
            case 'status':   return <span style={{ fontWeight: 700, color: STATUS_COLORS[val] || '#333', fontSize: 11 }}>{val}</span>;
            case 'class':    return <span style={{ fontWeight: 700, color: CLASS_COLORS[val] || '#333', fontSize: 11 }}>{val}</span>;
            case 'stage':    return (
                <span style={{ fontWeight: 700, fontSize: 11, color: val === 1 ? '#16a34a' : val === 2 ? '#d97706' : '#dc2626' }}>
                    S{val}
                </span>
            );
            case 'par':      return val
                ? <span style={{ color: '#dc2626', fontWeight: 700, fontSize: 11 }}>YES</span>
                : <span style={{ color: '#6b7280', fontSize: 11 }}>—</span>;
            default:         return String(val);
        }
    };

    return (
        <div>
            {/* Summary strip */}
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                {[
                    { label: 'Total Loans',      value: summary.total_loans?.toLocaleString() },
                    { label: 'Total Disbursed',  value: formatMoney(summary.total_disbursed) },
                    { label: 'Expected Interest',value: formatMoney(summary.total_expected_interest) },
                    { label: 'Total Outstanding',value: formatMoney(summary.total_outstanding) },
                    { label: 'PAR >30 Loans',    value: summary.par30_count, highlight: summary.par30_count > 0 },
                    { label: 'PAR >30 Amount',   value: formatMoney(summary.par30_amount), highlight: summary.par30_amount > 0 },
                    { label: 'PAR >30 Ratio',    value: `${summary.par30_ratio}%`, highlight: summary.par30_ratio > 5 },
                ].map(s => (
                    <div key={s.label} style={{
                        background: s.highlight ? '#FEF2F2' : 'var(--gray-50)',
                        border: `1px solid ${s.highlight ? '#FECACA' : 'var(--gray-100)'}`,
                        borderRadius: 8, padding: '10px 16px', minWidth: 140,
                    }}>
                        <div style={{ fontSize: 11, color: 'var(--gray-400)', marginBottom: 4 }}>{s.label}</div>
                        <div style={{ fontWeight: 700, fontSize: 15, color: s.highlight ? '#dc2626' : 'var(--gray-800)' }}>{s.value ?? '—'}</div>
                    </div>
                ))}
            </div>

            {/* Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {statuses.map(s => (
                        <button key={s} className={`btn btn-sm ${statusFilter === s ? 'btn-primary' : 'btn-secondary'}`}
                            onClick={() => setStatusFilter(s)}>
                            {s}
                        </button>
                    ))}
                </div>
                <button className="btn btn-secondary btn-sm"
                    onClick={() => exportCSV(rows, `disbursement-register-${report.generated_at}.csv`)}>
                    ⬇ Export CSV
                </button>
            </div>

            {/* Table */}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
                    <thead>
                        <tr style={{ background: '#f0f0f0', position: 'sticky', top: 0 }}>
                            {DR_COLS.map(c => (
                                <th key={c.key} style={{
                                    padding: '7px 10px', fontWeight: 700, fontSize: 11,
                                    textAlign: ['disbursed_amount','total_repayable','monthly_payment',
                                        'expected_interest','outstanding_balance','repaid_amount','monthly_income'].includes(c.key)
                                        ? 'right' : 'left',
                                    whiteSpace: 'nowrap', border: '1px solid #d0d0d0',
                                }}>
                                    {c.label}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {rows.length === 0 ? (
                            <tr><td colSpan={DR_COLS.length} style={{ textAlign: 'center', padding: 32, color: '#aaa' }}>No data</td></tr>
                        ) : rows.map((row: any, i: number) => (
                            <tr key={i} style={{
                                background: row.par_flag ? '#FFF5F5' : i % 2 === 0 ? '#fff' : '#fafafa',
                                borderLeft: row.par_flag ? '3px solid #dc2626' : '3px solid transparent',
                            }}>
                                {DR_COLS.map(col => (
                                    <td key={col.key} style={{
                                        padding: '5px 10px', border: '1px solid #e8e8e8',
                                        textAlign: ['disbursed_amount','total_repayable','monthly_payment',
                                            'expected_interest','outstanding_balance','repaid_amount','monthly_income'].includes(col.key)
                                            ? 'right' : 'left',
                                        whiteSpace: 'nowrap',
                                    }}>
                                        {renderCell(col, row[col.key])}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                    {/* Totals footer */}
                    {rows.length > 0 && (
                        <tfoot>
                            <tr style={{ background: '#f0f0f0', fontWeight: 700 }}>
                                {DR_COLS.map(col => {
                                    const numCols = ['disbursed_amount','total_repayable','expected_interest','repaid_amount','outstanding_balance','monthly_income'];
                                    if (col.key === 'client_name') return <td key={col.key} style={{ padding: '6px 10px', border: '1px solid #d0d0d0' }}>TOTAL ({rows.length})</td>;
                                    if (numCols.includes(col.key)) {
                                        const sum = rows.reduce((acc: number, r: any) => acc + (r[col.key] || 0), 0);
                                        return <td key={col.key} style={{ padding: '6px 10px', border: '1px solid #d0d0d0', textAlign: 'right' }}>{formatMoney(sum)}</td>;
                                    }
                                    return <td key={col.key} style={{ padding: '6px 10px', border: '1px solid #d0d0d0' }}></td>;
                                })}
                            </tr>
                        </tfoot>
                    )}
                </table>
            </div>
            <div style={{ fontSize: 11, color: '#aaa', marginTop: 8 }}>
                Generated: {report.generated_at} · {rows.length} records · PAR &gt;30 rows highlighted in red
            </div>
        </div>
    );
}

const AGING_BUCKETS = [
    { key: 'current',    label: 'Current',         days: '0' },
    { key: '1_30',       label: '30 Days',          days: '1-30' },
    { key: '31_60',      label: '60 Days',          days: '31-60' },
    { key: '61_90',      label: '90 Days',          days: '61-90' },
    { key: '91_120',     label: '120 Days',         days: '91-120' },
    { key: '121_150',    label: '150 Days',         days: '121-150' },
    { key: '151_180',    label: '180 Days',         days: '151-180' },
    { key: 'above_180',  label: 'Above 180 Days',   days: 'Above 180' },
];

function fmtN(n: number) {
    if (!n) return '-';
    return Math.round(n).toLocaleString();
}

function isMoneyField(key: string) {
    const normalized = key.toLowerCase();
    const nonMoneyFields = [
        'count', 'loan_count', 'total_loans', 'total_vintages', 'window_days',
        'days', 'days_overdue', 'days_until_due', 'mob', 'term_months',
        'avg_term_months', 'interest_rate', 'avg_interest_rate', 'pd', 'lgd',
        'par_ratio', 'par_30_ratio', 'par_90_ratio', 'par30_rate', 'par90_rate',
        'collection_rate', 'avg_collection_rate', 'loss_rate', 'default_rate',
        'fulfillment_rate', 'overdue_loans', 'active', 'closed', 'written_off',
        'broken', 'fulfilled', 'total'
    ];
    if (nonMoneyFields.includes(normalized)) return false;
    return [
        'amount', 'disbursed', 'repaid', 'repayable', 'outstanding', 'arrears',
        'expected', 'interest', 'income', 'principal', 'penalty', 'pipeline',
        'ecl', 'exposure', 'cash', 'inflows', 'outflows', 'net', 'balance'
    ].some(token => normalized.includes(token));
}

function formatReportValue(key: string, value: any) {
    if (typeof value === 'boolean') {
        return <span className={`badge ${value ? 'badge-success' : 'badge-error'}`}>{value ? 'Yes' : 'No'}</span>;
    }
    if (typeof value === 'number') {
        if (isMoneyField(key)) return formatMoney(value);
        return Number.isInteger(value) ? value.toLocaleString() : value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    }
    return String(value ?? '—');
}

function AgingProvisionTable({ data }: { data: any }) {
    const thBase: React.CSSProperties = {
        padding: '6px 10px', fontSize: 11, fontWeight: 700,
        textAlign: 'right', whiteSpace: 'nowrap', border: '1px solid #d0d0d0',
    };
    const td = (align: 'left' | 'right' = 'right'): React.CSSProperties => ({
        padding: '5px 10px', fontSize: 12, textAlign: align,
        border: '1px solid #e0e0e0', whiteSpace: 'nowrap',
    });
    const tdBold = (align: 'left' | 'right' = 'right'): React.CSSProperties => ({
        ...td(align), fontWeight: 700,
    });

    return (
        <div style={{ overflowX: 'auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10, fontSize: 13 }}>
                <strong>{data.report_date}</strong>
                <span style={{ color: '#555' }}>(Amounts in local currency ZMW)</span>
            </div>

            <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
                <thead>
                    {/* Days row */}
                    <tr style={{ background: '#f5f5f5' }}>
                        <th style={{ ...thBase, textAlign: 'left', width: 160 }}>Product</th>
                        <th style={thBase}>Total</th>
                        {AGING_BUCKETS.map(b => (
                            <th key={b.key} style={thBase}>{b.days}</th>
                        ))}
                    </tr>
                    {/* Column label row */}
                    <tr style={{ background: '#e8e8e8' }}>
                        <th style={{ ...thBase, textAlign: 'left' }}></th>
                        <th style={thBase}></th>
                        {AGING_BUCKETS.map(b => (
                            <th key={b.key} style={thBase}>{b.label}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {/* Product rows */}
                    {(data.rows || []).map((row: any, i: number) => (
                        <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#fafafa' }}>
                            <td style={{ ...td('left'), fontWeight: 600 }}>{row.product}</td>
                            <td style={td()}>{fmtN(row.total)}</td>
                            {AGING_BUCKETS.map(b => (
                                <td key={b.key} style={td()}>{fmtN(row[b.key])}</td>
                            ))}
                        </tr>
                    ))}

                    {/* Total row */}
                    <tr style={{ background: '#f0f0f0', borderTop: '2px solid #aaa' }}>
                        <td style={tdBold('left')}>Total</td>
                        <td style={tdBold()}>{fmtN(data.totals?.total)}</td>
                        {AGING_BUCKETS.map(b => (
                            <td key={b.key} style={tdBold()}>{fmtN(data.totals?.[b.key])}</td>
                        ))}
                    </tr>

                    {/* Spacer */}
                    <tr><td colSpan={10} style={{ padding: 6, border: 'none' }}></td></tr>

                    {/* EAD row */}
                    <tr style={{ background: '#c6efce' }}>
                        <td style={{ ...tdBold('left'), color: '#276221' }}>Exposure at Default (EAD)</td>
                        <td style={{ ...tdBold(), color: '#276221' }}>{fmtN(data.totals?.total)}</td>
                        {AGING_BUCKETS.map(b => (
                            <td key={b.key} style={{ ...tdBold(), color: '#276221' }}>{fmtN(data.totals?.[b.key])}</td>
                        ))}
                    </tr>

                    {/* PD% row */}
                    <tr>
                        <td style={{ ...td('left'), fontStyle: 'italic' }}>Probability of Default (PD%)</td>
                        <td style={td()}></td>
                        {AGING_BUCKETS.map(b => (
                            <td key={b.key} style={{ ...td(), fontStyle: 'italic', fontWeight: 600 }}>
                                {data.pd_rates?.[b.key] !== undefined
                                    ? `${Math.round(data.pd_rates[b.key] * 100)}%`
                                    : '-'}
                            </td>
                        ))}
                    </tr>

                    {/* Provision row */}
                    <tr style={{ background: '#fafafa' }}>
                        <td style={tdBold('left')}>Provision for Bad Debt (Total Impairment)</td>
                        <td style={tdBold()}>{fmtN(data.provision?.total)}</td>
                        {AGING_BUCKETS.map(b => (
                            <td key={b.key} style={tdBold()}>{fmtN(data.provision?.[b.key])}</td>
                        ))}
                    </tr>

                    {/* Spacer */}
                    <tr><td colSpan={10} style={{ padding: 4, border: 'none' }}></td></tr>

                    {/* PAR Ratios */}
                    <tr style={{ borderTop: '2px solid #aaa' }}>
                        <td style={td('left')}>PAR Ratios 30 Days</td>
                        <td style={{ ...td(), fontWeight: 700, color: data.par_30_ratio > 10 ? '#c00' : '#276221' }}>
                            {data.par_30_ratio}%
                        </td>
                        <td colSpan={8} style={{ border: '1px solid #e0e0e0' }}></td>
                    </tr>
                    <tr>
                        <td style={td('left')}>PAR Ratios 90 Days</td>
                        <td style={{ ...td(), fontWeight: 700, color: data.par_90_ratio > 5 ? '#c00' : '#276221' }}>
                            {data.par_90_ratio}%
                        </td>
                        <td colSpan={8} style={{ border: '1px solid #e0e0e0' }}></td>
                    </tr>
                </tbody>
            </table>
        </div>
    );
}

function ReportOutput({ data, reportId, ecWindowDays, onEcWindowChange, vaProduct, onVaProductChange }: { data: any; reportId: string; ecWindowDays?: number; onEcWindowChange?: (days: number) => void; vaProduct?: string; onVaProductChange?: (product: string) => void }) {
    // Render summary cards if available
    const renderSummary = () => {
        if (data.summary) {
            return (
                <div className="stat-grid" style={{ marginBottom: 20 }}>
                    {Object.entries(data.summary).map(([key, val]: any) => (
                        <div key={key} className="stat-card">
                            <div className="stat-value">{formatReportValue(key, val)}</div>
                            <div className="stat-label">{key.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}</div>
                        </div>
                    ))}
                </div>
            );
        }
        if (data.income) {
            return (
                <div className="stat-grid" style={{ marginBottom: 20 }}>
                    <div className="stat-card"><div className="stat-value" style={{ color: 'var(--success)' }}>{formatMoney(data.income.interest_income)}</div><div className="stat-label">Interest Income</div></div>
                    <div className="stat-card"><div className="stat-value">{formatMoney(data.income.repayment_principal_component)}</div><div className="stat-label">Principal Collected</div></div>
                    <div className="stat-card"><div className="stat-value" style={{ color: 'var(--warning)' }}>{formatMoney(data.income.penalty_income)}</div><div className="stat-label">Penalty Income</div></div>
                    <div className="stat-card"><div className="stat-value" style={{ color: 'var(--primary-600)' }}>{formatMoney(data.income.total_income)}</div><div className="stat-label">Total Income</div></div>
                    <div className="stat-card"><div className="stat-value" style={{ color: 'var(--error)' }}>{formatMoney(data.disbursements)}</div><div className="stat-label">Disbursements</div></div>
                </div>
            );
        }
        if (data.par_ratio !== undefined) {
            return (
                <div className="stat-grid" style={{ marginBottom: 20 }}>
                    <div className="stat-card"><div className="stat-value" style={{ color: data.par_ratio > 5 ? 'var(--error)' : 'var(--success)' }}>{data.par_ratio}%</div><div className="stat-label">PAR Ratio</div></div>
                    <div className="stat-card"><div className="stat-value">{formatMoney(data.par_amount)}</div><div className="stat-label">PAR Amount</div></div>
                </div>
            );
        }
        if (data.total_ecl !== undefined) {
            return (
                <div className="stat-grid" style={{ marginBottom: 20 }}>
                    <div className="stat-card"><div className="stat-value" style={{ color: 'var(--error)' }}>{formatMoney(data.total_ecl)}</div><div className="stat-label">Total ECL</div></div>
                </div>
            );
        }
        return null;
    };

    // Render data table
    const renderTable = () => {
        const tableData = data.data || data.accounts || data.cohorts || data.stages || data.by_product || [];
        if (!tableData.length) return <div className="empty-state"><div className="empty-state-icon">📊</div><h3>No Data</h3><p>No records found for this report.</p></div>;

        const keys = Object.keys(tableData[0]);
        return (
            <div className="table-container">
                <table>
                    <thead>
                        <tr>
                            {keys.map(k => <th key={k}>{k.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</th>)}
                        </tr>
                    </thead>
                    <tbody>
                        {tableData.slice(0, 50).map((row: any, i: number) => (
                            <tr key={i}>
                                {keys.map(k => (
                                    <td key={k}>
                                        {typeof row[k] === 'number' && k.includes('amount') || k.includes('total') || k.includes('outstanding') || k.includes('ecl') || k.includes('exposure')
                                            ? formatMoney(row[k])
                                            : typeof row[k] === 'boolean'
                                                ? <span className={`badge ${row[k] ? 'badge-success' : 'badge-error'}`}>{row[k] ? 'Yes' : 'No'}</span>
                                                : String(row[k] ?? '—')}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    if (reportId === 'disbursement-register' && data.summary) {
        return <DisbursementRegisterTable data={data} />;
    }
    if (reportId === 'aging-par-report' && data.rows) {
        return <AgingProvisionTable data={data} />;
    }
    if (reportId === 'expected-collection' && data.summary) {
        return <ExpectedCollectionTable data={data} windowDays={ecWindowDays ?? 30} onWindowChange={onEcWindowChange ?? (() => {})} />;
    }
    if (reportId === 'vintage-analysis' && data.cohorts) {
        return <VintageAnalysisTable data={data} selectedProduct={vaProduct ?? ''} onProductChange={onVaProductChange ?? (() => {})} />;
    }

    return (
        <div>
            {renderSummary()}
            {renderTable()}
        </div>
    );
}

function ExpectedCollectionTable({ data: report, windowDays, onWindowChange }: { data: any; windowDays: number; onWindowChange: (days: number) => void }) {
    const rows: any[] = report.data || [];
    const s = report.summary || {};

    const exportCSV = () => {
        const cols = ['loan_number','client_name','client_phone','product','installment_no','due_date','days_until_due','installment_amount','arrears','total_expected','expected_interest','outstanding_balance','days_overdue','ptp_status','ptp_date','ptp_amount','collection_priority'];
        const header = cols.join(',');
        const body = rows.map(r => cols.map(c => {
            const v = r[c] ?? '';
            return typeof v === 'string' && v.includes(',') ? `"${v}"` : v;
        }).join(',')).join('\n');
        const blob = new Blob([header + '\n' + body], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url;
        a.download = `expected_collection_${windowDays}d_${report.generated_at}.csv`;
        a.click(); URL.revokeObjectURL(url);
    };

    const priorityColor = (p: string) => p === 'High' ? 'badge-error' : p === 'Medium' ? 'badge-warning' : 'badge-success';
    const ptpBadge = (s: string) => {
        if (s === 'ACTIVE') return 'badge-info';
        if (s === 'FULFILLED') return 'badge-success';
        if (s === 'BROKEN') return 'badge-error';
        return 'badge-gray';
    };

    return (
        <div>
            {/* Window selector */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-600)' }}>Collection Window:</span>
                {[7, 30, 60].map(d => (
                    <button key={d} className={`btn btn-sm ${windowDays === d ? 'btn-primary' : 'btn-secondary'}`} onClick={() => onWindowChange(d)}>
                        {d} Days
                    </button>
                ))}
                <button className="btn btn-sm btn-secondary" style={{ marginLeft: 'auto' }} onClick={exportCSV}>Export CSV</button>
            </div>

            {/* Summary cards */}
            <div className="stat-grid" style={{ marginBottom: 20 }}>
                <div className="stat-card">
                    <div className="stat-value">{s.total_loans_due ?? 0}</div>
                    <div className="stat-label">Loans Due</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--primary-600)' }}>{formatMoney(s.total_expected)}</div>
                    <div className="stat-label">Total Expected</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--success)' }}>{formatMoney(s.total_expected_interest)}</div>
                    <div className="stat-label">Expected Interest</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: s.overdue_loans > 0 ? 'var(--error)' : 'var(--success)' }}>{s.overdue_loans ?? 0}</div>
                    <div className="stat-label">Overdue Loans</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--error)' }}>{formatMoney(s.total_arrears)}</div>
                    <div className="stat-label">Total Arrears</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--info)' }}>{formatMoney(s.ptp_pipeline)}</div>
                    <div className="stat-label">PTP Pipeline</div>
                </div>
            </div>

            {/* Table */}
            {rows.length === 0 ? (
                <div className="empty-state"><div className="empty-state-icon">📅</div><h3>No Collections Due</h3><p>No loans have installments due in the next {windowDays} days.</p></div>
            ) : (
                <div className="table-container" style={{ overflowX: 'auto' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Loan No.</th>
                                <th>Client</th>
                                <th>Phone</th>
                                <th>Product</th>
                                <th>Installment</th>
                                <th>Due Date</th>
                                <th>Days</th>
                                <th>Installment Amt</th>
                                <th>Arrears</th>
                                <th>Total Expected</th>
                                <th>Expected Interest</th>
                                <th>Outstanding Bal.</th>
                                <th>DPD</th>
                                <th>PTP Status</th>
                                <th>PTP Date</th>
                                <th>PTP Amount</th>
                                <th>Priority</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((r, i) => {
                                const isOverdue = r.days_until_due < 0;
                                return (
                                    <tr key={i} style={isOverdue ? { background: '#fff5f5' } : undefined}>
                                        <td>{i + 1}</td>
                                        <td style={{ fontWeight: 600 }}>{r.loan_number}</td>
                                        <td>{r.client_name}</td>
                                        <td>{r.client_phone}</td>
                                        <td>{r.product}</td>
                                        <td>{r.installment_no}</td>
                                        <td>{r.due_date}</td>
                                        <td style={{ color: isOverdue ? 'var(--error)' : r.days_until_due <= 7 ? 'var(--warning)' : 'inherit', fontWeight: isOverdue ? 700 : 400 }}>
                                            {isOverdue ? `${Math.abs(r.days_until_due)}d overdue` : `in ${r.days_until_due}d`}
                                        </td>
                                        <td>{formatMoney(r.installment_amount)}</td>
                                        <td style={{ color: r.arrears > 0 ? 'var(--error)' : 'inherit' }}>
                                            {r.arrears > 0 ? formatMoney(r.arrears) : '—'}
                                        </td>
                                        <td style={{ fontWeight: 600 }}>{formatMoney(r.total_expected)}</td>
                                        <td>{formatMoney(r.expected_interest)}</td>
                                        <td>{formatMoney(r.outstanding_balance)}</td>
                                        <td style={{ color: r.days_overdue > 0 ? 'var(--error)' : 'inherit' }}>{r.days_overdue}</td>
                                        <td>{r.ptp_status && r.ptp_status !== 'NONE' ? <span className={`badge ${ptpBadge(r.ptp_status)}`}>{r.ptp_status}</span> : '—'}</td>
                                        <td>{r.ptp_date ?? '—'}</td>
                                        <td>{r.ptp_amount ? formatMoney(r.ptp_amount) : '—'}</td>
                                        <td><span className={`badge ${priorityColor(r.collection_priority)}`}>{r.collection_priority}</span></td>
                                    </tr>
                                );
                            })}
                        </tbody>
                        <tfoot>
                            <tr style={{ fontWeight: 700, background: 'var(--gray-50)' }}>
                                <td colSpan={8}>Totals ({rows.length} loans)</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + Number(r.installment_amount), 0))}</td>
                                <td style={{ color: 'var(--error)' }}>{formatMoney(rows.reduce((a, r) => a + Number(r.arrears), 0))}</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + Number(r.total_expected), 0))}</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + Number(r.expected_interest), 0))}</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + Number(r.outstanding_balance), 0))}</td>
                                <td colSpan={5}></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            )}
        </div>
    );
}

function VintageAnalysisTable({ data: report, selectedProduct, onProductChange }: { data: any; selectedProduct: string; onProductChange: (p: string) => void }) {
    const rows: any[] = report.cohorts || [];
    const s = report.summary || {};
    const products: string[] = report.products || [];

    const parColor = (rate: number) => {
        if (rate === 0) return 'var(--success)';
        if (rate < 5) return 'var(--warning)';
        return 'var(--error)';
    };

    const collColor = (rate: number) => {
        if (rate >= 90) return 'var(--success)';
        if (rate >= 70) return 'var(--warning)';
        return 'var(--error)';
    };

    const statusBadge = (st: string) => {
        if (st === 'Mature') return 'badge-gray';
        if (st === 'Seasoned') return 'badge-info';
        return 'badge-success';
    };

    const exportCSV = () => {
        const cols = ['vintage','mob','vintage_status','count','disbursed','expected_interest','avg_loan_size','avg_term_months','avg_interest_rate','active','closed','written_off','repaid','outstanding','par30_rate','par90_rate','collection_rate','loss_rate','default_rate'];
        const header = cols.join(',');
        const body = rows.map(r => cols.map(c => r[c] ?? '').join(',')).join('\n');
        const blob = new Blob([header + '\n' + body], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a'); a.href = url;
        a.download = `vintage_analysis_${report.generated_at}.csv`;
        a.click(); URL.revokeObjectURL(url);
    };

    return (
        <div>
            {/* Controls */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--gray-600)' }}>Product:</span>
                <select
                    className="form-control"
                    style={{ width: 'auto', minWidth: 160, padding: '4px 10px', height: 34 }}
                    value={selectedProduct}
                    onChange={e => onProductChange(e.target.value)}
                >
                    <option value="">All Products</option>
                    {products.map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <button className="btn btn-sm btn-secondary" style={{ marginLeft: 'auto' }} onClick={exportCSV}>Export CSV</button>
            </div>

            {/* Summary cards */}
            <div className="stat-grid" style={{ marginBottom: 20 }}>
                <div className="stat-card">
                    <div className="stat-value">{s.total_vintages ?? 0}</div>
                    <div className="stat-label">Vintages</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{s.total_loans ?? 0}</div>
                    <div className="stat-label">Total Loans</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--primary-600)' }}>{formatMoney(s.total_disbursed)}</div>
                    <div className="stat-label">Total Disbursed</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--success)' }}>{formatMoney(s.total_expected_interest)}</div>
                    <div className="stat-label">Expected Interest</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--success)' }}>{formatMoney(s.total_repaid)}</div>
                    <div className="stat-label">Total Repaid</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: collColor(s.avg_collection_rate ?? 0) }}>{s.avg_collection_rate ?? 0}%</div>
                    <div className="stat-label">Avg Collection Rate</div>
                </div>
            </div>

            {/* Table */}
            {rows.length === 0 ? (
                <div className="empty-state"><div className="empty-state-icon">📊</div><h3>No Data</h3><p>No disbursed loans found for this filter.</p></div>
            ) : (
                <div className="table-container" style={{ overflowX: 'auto' }}>
                    <table>
                        <thead>
                            <tr>
                                <th>Vintage</th>
                                <th>MOB</th>
                                <th>Status</th>
                                <th>Loans</th>
                                <th>Disbursed</th>
                                <th>Expected Interest</th>
                                <th>Avg Loan</th>
                                <th>Avg Term</th>
                                <th>Avg Rate</th>
                                <th>Active</th>
                                <th>Closed</th>
                                <th>Written Off</th>
                                <th>Repaid</th>
                                <th>Outstanding</th>
                                <th>PAR30%</th>
                                <th>PAR90%</th>
                                <th>Collection %</th>
                                <th>Loss %</th>
                                <th>Default %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((r, i) => (
                                <tr key={i}>
                                    <td style={{ fontWeight: 700 }}>{r.vintage}</td>
                                    <td>{r.mob}</td>
                                    <td><span className={`badge ${statusBadge(r.vintage_status)}`}>{r.vintage_status}</span></td>
                                    <td>{r.count}</td>
                                    <td>{formatMoney(r.disbursed)}</td>
                                    <td>{formatMoney(r.expected_interest)}</td>
                                    <td>{formatMoney(r.avg_loan_size)}</td>
                                    <td>{r.avg_term_months}m</td>
                                    <td>{r.avg_interest_rate}%</td>
                                    <td>{r.active}</td>
                                    <td>{r.closed}</td>
                                    <td style={{ color: r.written_off > 0 ? 'var(--error)' : 'inherit' }}>{r.written_off}</td>
                                    <td>{formatMoney(r.repaid)}</td>
                                    <td>{formatMoney(r.outstanding)}</td>
                                    <td style={{ fontWeight: 600, color: parColor(r.par30_rate) }}>{r.par30_rate}%</td>
                                    <td style={{ fontWeight: 600, color: parColor(r.par90_rate) }}>{r.par90_rate}%</td>
                                    <td style={{ fontWeight: 600, color: collColor(r.collection_rate) }}>{r.collection_rate}%</td>
                                    <td style={{ color: r.loss_rate > 0 ? 'var(--error)' : 'inherit' }}>{r.loss_rate}%</td>
                                    <td style={{ fontWeight: 600, color: parColor(r.default_rate) }}>{r.default_rate}%</td>
                                </tr>
                            ))}
                        </tbody>
                        <tfoot>
                            <tr style={{ fontWeight: 700, background: 'var(--gray-50)' }}>
                                <td colSpan={3}>Totals ({rows.length} vintages)</td>
                                <td>{rows.reduce((a, r) => a + r.count, 0)}</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + r.disbursed, 0))}</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + r.expected_interest, 0))}</td>
                                <td colSpan={3}></td>
                                <td>{rows.reduce((a, r) => a + r.active, 0)}</td>
                                <td>{rows.reduce((a, r) => a + r.closed, 0)}</td>
                                <td>{rows.reduce((a, r) => a + r.written_off, 0)}</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + r.repaid, 0))}</td>
                                <td>{formatMoney(rows.reduce((a, r) => a + r.outstanding, 0))}</td>
                                <td colSpan={5}></td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            )}

            {/* Legend */}
            <div style={{ marginTop: 12, display: 'flex', gap: 16, fontSize: 12, color: 'var(--gray-500)' }}>
                <span><b>MOB</b> = Months on Book since disbursement</span>
                <span><b>PAR%</b> = Outstanding balance of overdue loans / Total disbursed</span>
                <span><b>Collection%</b> = Total repaid / Total repayable</span>
                <span style={{ color: 'var(--success)' }}>● Good</span>
                <span style={{ color: 'var(--warning)' }}>● Watch</span>
                <span style={{ color: 'var(--error)' }}>● At Risk</span>
            </div>
        </div>
    );
}

function getMockReportData(reportId: string) {
    const today = new Date().toISOString().split('T')[0];
    const mocks: Record<string, any> = {
        'active-loan-portfolio': {
            report: 'Active Loan Portfolio',
            summary: { total_loans: 89, total_disbursed: 1250000, total_outstanding: 980000 },
            by_product: [
                { product__name: 'IntZam Personal', count: 65, total: 850000 },
                { product__name: 'SME Growth', count: 24, total: 400000 },
            ],
            generated_at: today,
        },
        'aging-par-report': {
            report: 'Aging PAR Report',
            par_ratio: 4.2,
            par_amount: 41160,
            buckets: {
                '1-30': { count: 8, loans: [] },
                '31-60': { count: 3, loans: [] },
                '61-90': { count: 1, loans: [] },
                '90+': { count: 0, loans: [] },
            },
            generated_at: today,
        },
        'income-statement': {
            report: 'Income Statement',
            period: `${today.slice(0, 7)}-01 to ${today}`,
            income: { interest_income: 72000, penalty_income: 8500, total_income: 80500 },
            disbursements: 85000,
            generated_at: today,
        },
        'ifrs9-expected-loss': {
            report: 'IFRS 9 Expected Loss',
            total_ecl: 47250,
            stages: [
                { stage: 'Stage 1', loan_count: 75, exposure: 850000, pd: 0.02, lgd: 0.45, ecl: 7650 },
                { stage: 'Stage 2', loan_count: 10, exposure: 120000, pd: 0.15, lgd: 0.55, ecl: 9900 },
                { stage: 'Stage 3', loan_count: 4, exposure: 50000, pd: 0.80, lgd: 0.75, ecl: 30000 },
            ],
            generated_at: today,
        },
    };
    return mocks[reportId] || { report: reportId, data: [], generated_at: today };
}
