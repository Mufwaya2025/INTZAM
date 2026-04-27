import { useState, useEffect } from 'react';
import { reportsAPI } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { formatMoney } from '../utils/format';

const COLORS = ['#7c3aed', '#10b981', '#f59e0b', '#ef4444', '#3b82f6'];

export default function DashboardPage() {
    const [stats, setStats] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        reportsAPI.dashboardStats()
            .then(res => setStats(res.data))
            .catch(() => setStats(getMockStats()))
            .finally(() => setLoading(false));
    }, []);

    if (loading) return <div className="loading-overlay"><div className="loading-spinner" style={{ width: 40, height: 40 }}></div></div>;

    const s = stats || getMockStats();

    const portfolioData = [
        { name: 'Active', value: s.active_loans },
        { name: 'Overdue', value: s.overdue_loans },
        { name: 'Pending', value: s.pending_loans },
        { name: 'Closed', value: Math.max(0, s.total_clients - s.active_loans - s.overdue_loans - s.pending_loans) },
    ];

    const monthlyData = s.monthly_performance || [];

    return (
        <div>
            {/* Stats Grid */}
            <div className="stat-grid">
                <StatCard
                    icon="👥"
                    iconClass="purple"
                    value={s.total_clients}
                    label="Total Clients"
                />
                <StatCard
                    icon="💰"
                    iconClass="green"
                    value={formatMoney(s.total_portfolio)}
                    label="Active Portfolio"
                />
                <StatCard
                    icon="⚠️"
                    iconClass="amber"
                    value={s.overdue_loans}
                    label="Overdue Loans"
                    change={`PAR: ${s.par_ratio}%`}
                    positive={s.par_ratio < 5}
                />
                <StatCard
                    icon="⏳"
                    iconClass="blue"
                    value={s.pending_loans}
                    label="Pending Approval"
                    change="Awaiting review"
                />
                <StatCard
                    icon="📥"
                    iconClass="green"
                    value={formatMoney(s.monthly_disbursed)}
                    label="Monthly Disbursed"
                    change="This month"
                />
                <StatCard
                    icon="📤"
                    iconClass="purple"
                    value={formatMoney(s.monthly_collected)}
                    label="Monthly Collected"
                    change="This month"
                />
            </div>

            {/* Charts Row */}
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 20, marginBottom: 24 }}>
                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Monthly Performance</h3>
                        <span className="badge badge-purple">Last 5 months</span>
                    </div>
                    <div className="card-body">
                        <ResponsiveContainer width="100%" height={240}>
                            <BarChart data={monthlyData}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                                <YAxis tick={{ fontSize: 12 }} tickFormatter={v => formatMoney(v)} width={110} />
                                <Tooltip formatter={(v: any) => [formatMoney(v), '']} />
                                <Bar dataKey="disbursed" fill="#7c3aed" radius={[4, 4, 0, 0]} name="Disbursed" />
                                <Bar dataKey="collected" fill="#10b981" radius={[4, 4, 0, 0]} name="Collected" />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div className="card">
                    <div className="card-header">
                        <h3 className="card-title">Portfolio Mix</h3>
                    </div>
                    <div className="card-body">
                        <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                                <Pie data={portfolioData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} dataKey="value">
                                    {portfolioData.map((_, i) => (
                                        <Cell key={i} fill={COLORS[i]} />
                                    ))}
                                </Pie>
                                <Tooltip />
                            </PieChart>
                        </ResponsiveContainer>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                            {portfolioData.map((item, i) => (
                                <div key={item.name} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 12 }}>
                                    <div style={{ width: 10, height: 10, borderRadius: 2, background: COLORS[i] }}></div>
                                    <span style={{ color: 'var(--gray-600)' }}>{item.name}: {item.value}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* PAR Alert */}
            {s.par_ratio > 5 && (
                <div className="alert alert-warning" style={{ marginBottom: 24 }}>
                    <span>⚠️</span>
                    <div>
                        <strong>PAR Alert:</strong> Portfolio at Risk is {s.par_ratio}% ({formatMoney(s.par_amount)}).
                        This exceeds the 5% threshold. Review collections immediately.
                    </div>
                </div>
            )}

            {/* Quick Actions */}
            <div className="card">
                <div className="card-header">
                    <h3 className="card-title">Quick Actions</h3>
                </div>
                <div className="card-body">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12 }}>
                        {[
                            { icon: '✅', label: 'Review Pending Loans', color: '#7c3aed', count: s.pending_loans },
                            { icon: '📞', label: 'Collections Queue', color: '#f59e0b', count: s.overdue_loans },
                            { icon: '📊', label: 'Generate Reports', color: '#3b82f6', count: null },
                            { icon: '👥', label: 'New Client', color: '#10b981', count: null },
                        ].map(action => (
                            <div key={action.label} style={{
                                padding: 20,
                                borderRadius: 16,
                                border: `1px solid ${action.color}30`,
                                background: `rgba(255, 255, 255, 0.7)`,
                                backdropFilter: 'blur(12px)',
                                WebkitBackdropFilter: 'blur(12px)',
                                boxShadow: `0 4px 16px ${action.color}15`,
                                cursor: 'pointer',
                                transition: 'all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)',
                            }}
                                onMouseEnter={e => {
                                    e.currentTarget.style.transform = 'translateY(-4px) scale(1.02)';
                                    e.currentTarget.style.boxShadow = `0 12px 24px ${action.color}30`;
                                }}
                                onMouseLeave={e => {
                                    e.currentTarget.style.transform = 'none';
                                    e.currentTarget.style.boxShadow = `0 4px 16px ${action.color}15`;
                                }}
                            >
                                <div style={{ fontSize: 26, marginBottom: 12 }}>{action.icon}</div>
                                <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--gray-800)' }}>{action.label}</div>
                                {action.count !== null && (
                                    <div style={{ fontSize: 24, fontWeight: 800, color: action.color, marginTop: 6, fontFamily: "'Outfit', sans-serif" }}>{action.count}</div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

function StatCard({ icon, iconClass, value, label, change, positive }: any) {
    return (
        <div className="stat-card">
            <div className={`stat-icon ${iconClass}`}>
                <span style={{ fontSize: 20 }}>{icon}</span>
            </div>
            <div className="stat-value">{value}</div>
            <div className="stat-label">{label}</div>
            {change && (
                <div className={`stat-change ${positive ? 'positive' : ''}`}>
                    {positive ? '↑' : ''} {change}
                </div>
            )}
        </div>
    );
}

function getMockStats() {
    return {
        total_clients: 0,
        active_loans: 0,
        overdue_loans: 0,
        pending_loans: 0,
        total_portfolio: 0,
        total_outstanding: 0,
        total_repaid: 0,
        monthly_disbursed: 0,
        monthly_collected: 0,
        par_ratio: 0,
        par_amount: 0,
        monthly_performance: [],
    };
}
