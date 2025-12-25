'use client';

import React, { useState, useEffect } from 'react';

interface Rule {
    id: string;
    name: string;
    action: string;
    scope: string;
    priority: number;
    is_active: boolean;
}

interface Plugin {
    id: string;
    name: string;
    version: string;
    status: string;
    execution_count: number;
    error_count: number;
}

interface StaffingPrediction {
    recommended_headcount: number;
    confidence_band: string;
    confidence_level: string;
    time_horizon: string;
    assumptions: string[];
}

const API_BASE = 'http://localhost:8000/api/v1/advanced';

export function ExtensionsDashboard() {
    const [activeTab, setActiveTab] = useState<'rules' | 'workflows' | 'plugins' | 'predictions'>('rules');
    const [rules, setRules] = useState<Rule[]>([]);
    const [plugins, setPlugins] = useState<Plugin[]>([]);
    const [flags, setFlags] = useState<Record<string, boolean>>({});
    const [prediction, setPrediction] = useState<StaffingPrediction | null>(null);
    const [loading, setLoading] = useState(true);
    const [showNewRule, setShowNewRule] = useState(false);
    const [newRule, setNewRule] = useState({
        name: '',
        action: 'recommend',
        scope: 'all',
        priority: 50,
        condition_field: '',
        condition_operator: 'equals',
        condition_value: ''
    });

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [rulesRes, pluginsRes, flagsRes] = await Promise.allSettled([
                fetch(`${API_BASE}/rules`),
                fetch(`${API_BASE}/plugins`),
                fetch(`${API_BASE}/feature-flags`)
            ]);

            if (rulesRes.status === 'fulfilled' && rulesRes.value.ok) {
                setRules(await rulesRes.value.json());
            }
            if (pluginsRes.status === 'fulfilled' && pluginsRes.value.ok) {
                setPlugins(await pluginsRes.value.json());
            }
            if (flagsRes.status === 'fulfilled' && flagsRes.value.ok) {
                setFlags(await flagsRes.value.json());
            }
        } catch (err) {
            console.error('Failed to fetch data:', err);
        } finally {
            setLoading(false);
        }
    };

    const createRule = async () => {
        try {
            const response = await fetch(`${API_BASE}/rules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: newRule.name,
                    action: newRule.action,
                    scope: newRule.scope,
                    priority: newRule.priority,
                    condition: {
                        field: newRule.condition_field,
                        operator: newRule.condition_operator,
                        value: newRule.condition_value
                    }
                })
            });

            if (response.ok) {
                setShowNewRule(false);
                setNewRule({
                    name: '',
                    action: 'recommend',
                    scope: 'all',
                    priority: 50,
                    condition_field: '',
                    condition_operator: 'equals',
                    condition_value: ''
                });
                fetchData();
            }
        } catch (err) {
            console.error('Failed to create rule:', err);
        }
    };

    const fetchPrediction = async () => {
        try {
            const response = await fetch(`${API_BASE}/predictions/staffing`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ time_horizon: 'next_quarter' })
            });

            if (response.ok) {
                setPrediction(await response.json());
            }
        } catch (err) {
            console.error('Failed to fetch prediction:', err);
        }
    };

    const getActionColor = (action: string) => {
        switch (action) {
            case 'recommend': return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
            case 'block': return 'bg-red-500/20 text-red-300 border-red-500/30';
            case 'require_approval': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
            default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
        }
    };

    const getPluginStatusColor = (status: string) => {
        switch (status) {
            case 'active': return 'bg-green-500';
            case 'approved': return 'bg-blue-500';
            case 'pending': return 'bg-yellow-500';
            case 'disabled': return 'bg-red-500';
            default: return 'bg-gray-500';
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-400"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900/20 to-slate-900 p-6">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-white">Extensions & Customization</h1>
                        <p className="text-purple-300 mt-1">
                            Rules Engine • Workflows • Plugins • Predictions
                        </p>
                    </div>
                    <button
                        onClick={fetchData}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                    >
                        Refresh
                    </button>
                </div>

                {/* Sandbox Notice */}
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-xl p-4">
                    <div className="flex items-center gap-2 text-purple-300">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-medium">Sandboxed Extension Platform</span>
                    </div>
                    <p className="text-gray-400 text-sm mt-1">
                        Extensions produce recommendations only. All actions require approval and flow through security controls.
                    </p>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 bg-slate-800/50 p-1 rounded-lg w-fit">
                    {(['rules', 'workflows', 'plugins', 'predictions'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={`px-4 py-2 rounded-md transition-colors capitalize ${activeTab === tab
                                    ? 'bg-purple-600 text-white'
                                    : 'text-purple-300 hover:bg-purple-600/20'
                                }`}
                        >
                            {tab}
                        </button>
                    ))}
                </div>

                {/* Rules Tab */}
                {activeTab === 'rules' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center">
                            <h2 className="text-xl font-semibold text-white">Organization Rules</h2>
                            <button
                                onClick={() => setShowNewRule(true)}
                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
                            >
                                + Add Rule
                            </button>
                        </div>

                        {rules.length === 0 ? (
                            <div className="bg-slate-800/50 rounded-xl border border-purple-500/20 p-12 text-center">
                                <div className="text-4xl mb-4">📋</div>
                                <p className="text-purple-300">No rules defined yet</p>
                                <p className="text-gray-400 text-sm mt-2">Create rules to customize behavior for your organization</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {rules.map((rule) => (
                                    <div key={rule.id} className="bg-slate-800/50 rounded-xl border border-purple-500/20 p-4">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-3">
                                                <span className={`w-2 h-2 rounded-full ${rule.is_active ? 'bg-green-400' : 'bg-gray-400'}`}></span>
                                                <span className="text-white font-medium">{rule.name}</span>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <span className={`px-2 py-1 rounded border text-xs ${getActionColor(rule.action)}`}>
                                                    {rule.action.replace('_', ' ')}
                                                </span>
                                                <span className="text-gray-400 text-sm">Priority: {rule.priority}</span>
                                            </div>
                                        </div>
                                        <div className="mt-2 text-gray-400 text-sm">
                                            Scope: <span className="text-purple-300">{rule.scope}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Workflows Tab */}
                {activeTab === 'workflows' && (
                    <div className="bg-slate-800/50 rounded-xl border border-purple-500/20 p-12 text-center">
                        <div className="text-4xl mb-4">🔄</div>
                        <p className="text-purple-300">Workflow Builder</p>
                        <p className="text-gray-400 text-sm mt-2">Create custom DAG workflows with validation</p>
                        <p className="text-yellow-400 text-xs mt-4">Visual workflow builder coming soon</p>
                    </div>
                )}

                {/* Plugins Tab */}
                {activeTab === 'plugins' && (
                    <div className="space-y-6">
                        <h2 className="text-xl font-semibold text-white">Plugin Registry</h2>

                        {plugins.length === 0 ? (
                            <div className="bg-slate-800/50 rounded-xl border border-purple-500/20 p-12 text-center">
                                <div className="text-4xl mb-4">🔌</div>
                                <p className="text-purple-300">No plugins registered</p>
                                <p className="text-gray-400 text-sm mt-2">Plugins run in sandboxed environments with timeouts</p>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {plugins.map((plugin) => (
                                    <div key={plugin.id} className="bg-slate-800/50 rounded-xl border border-purple-500/20 p-4">
                                        <div className="flex items-center justify-between mb-2">
                                            <span className="text-white font-medium">{plugin.name}</span>
                                            <span className={`w-2 h-2 rounded-full ${getPluginStatusColor(plugin.status)}`}></span>
                                        </div>
                                        <div className="text-gray-400 text-sm">
                                            v{plugin.version} • {plugin.execution_count} runs
                                            {plugin.error_count > 0 && (
                                                <span className="text-red-400 ml-2">({plugin.error_count} errors)</span>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Predictions Tab */}
                {activeTab === 'predictions' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center">
                            <h2 className="text-xl font-semibold text-white">Predictive Staffing</h2>
                            <button
                                onClick={fetchPrediction}
                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm"
                            >
                                Generate Prediction
                            </button>
                        </div>

                        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-yellow-300 text-sm">
                            ⚠️ Predictions are recommendations only. Cannot trigger hiring actions.
                        </div>

                        {prediction ? (
                            <div className="bg-slate-800/50 rounded-xl border border-purple-500/20 p-6">
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                                    <div className="text-center">
                                        <div className="text-3xl font-bold text-purple-400">{prediction.recommended_headcount}</div>
                                        <div className="text-gray-400 text-sm">Recommended</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-2xl font-bold text-white">{prediction.confidence_band}</div>
                                        <div className="text-gray-400 text-sm">Confidence Band</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-2xl font-bold text-green-400">{prediction.confidence_level}</div>
                                        <div className="text-gray-400 text-sm">Confidence</div>
                                    </div>
                                    <div className="text-center">
                                        <div className="text-xl font-medium text-gray-300">{prediction.time_horizon}</div>
                                        <div className="text-gray-400 text-sm">Time Horizon</div>
                                    </div>
                                </div>

                                <div>
                                    <h4 className="text-purple-300 font-medium mb-2">Assumptions</h4>
                                    <ul className="text-gray-400 text-sm space-y-1">
                                        {prediction.assumptions.map((a, i) => (
                                            <li key={i}>• {a}</li>
                                        ))}
                                    </ul>
                                </div>
                            </div>
                        ) : (
                            <div className="bg-slate-800/50 rounded-xl border border-purple-500/20 p-12 text-center">
                                <div className="text-4xl mb-4">📊</div>
                                <p className="text-purple-300">Click "Generate Prediction" to analyze staffing needs</p>
                            </div>
                        )}
                    </div>
                )}

                {/* New Rule Modal */}
                {showNewRule && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                        <div className="bg-slate-800 rounded-xl border border-purple-500/30 p-6 w-full max-w-lg">
                            <h3 className="text-xl font-semibold text-white mb-4">Create Rule</h3>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Rule Name</label>
                                    <input
                                        type="text"
                                        value={newRule.name}
                                        onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-purple-300 text-sm mb-1">Action</label>
                                        <select
                                            value={newRule.action}
                                            onChange={(e) => setNewRule({ ...newRule, action: e.target.value })}
                                            className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white"
                                        >
                                            <option value="recommend">Recommend</option>
                                            <option value="block">Block</option>
                                            <option value="require_approval">Require Approval</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-purple-300 text-sm mb-1">Scope</label>
                                        <select
                                            value={newRule.scope}
                                            onChange={(e) => setNewRule({ ...newRule, scope: e.target.value })}
                                            className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white"
                                        >
                                            <option value="all">All</option>
                                            <option value="tasks">Tasks</option>
                                            <option value="people">People</option>
                                            <option value="finance">Finance</option>
                                            <option value="hiring">Hiring</option>
                                        </select>
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Condition Field</label>
                                    <input
                                        type="text"
                                        value={newRule.condition_field}
                                        onChange={(e) => setNewRule({ ...newRule, condition_field: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white"
                                        placeholder="e.g., priority, status, amount"
                                    />
                                </div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-purple-300 text-sm mb-1">Operator</label>
                                        <select
                                            value={newRule.condition_operator}
                                            onChange={(e) => setNewRule({ ...newRule, condition_operator: e.target.value })}
                                            className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white"
                                        >
                                            <option value="equals">Equals</option>
                                            <option value="not_equals">Not Equals</option>
                                            <option value="greater_than">Greater Than</option>
                                            <option value="less_than">Less Than</option>
                                            <option value="contains">Contains</option>
                                        </select>
                                    </div>
                                    <div>
                                        <label className="block text-purple-300 text-sm mb-1">Value</label>
                                        <input
                                            type="text"
                                            value={newRule.condition_value}
                                            onChange={(e) => setNewRule({ ...newRule, condition_value: e.target.value })}
                                            className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white"
                                        />
                                    </div>
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 mt-6">
                                <button
                                    onClick={() => setShowNewRule(false)}
                                    className="px-4 py-2 text-purple-300 hover:text-white transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={createRule}
                                    disabled={!newRule.name || !newRule.condition_field}
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white rounded-lg transition-colors"
                                >
                                    Create Rule
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default ExtensionsDashboard;
