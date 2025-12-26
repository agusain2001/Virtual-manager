'use client';

import React, { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface Approval {
    id: string;
    agent_name: string;
    action_type: string;
    action_summary: string;
    risk_score: number;
    sensitivity: string;
    resource_type: string | null;
    resource_id: string | null;
    requester_name: string;
    requested_at: string;
    impact_summary: string;
    is_reversible: boolean;
}

type Props = {
    isOpen: boolean;
    onClose: () => void;
    onDecision?: (approved: boolean) => void;
}

export default function InterventionModal({ isOpen, onClose, onDecision }: Props) {
    const [approvals, setApprovals] = useState<Approval[]>([]);
    const [loading, setLoading] = useState(false);
    const [deciding, setDeciding] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (isOpen) {
            fetchApprovals();
        }
    }, [isOpen]);

    const fetchApprovals = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`${API_URL}/managerial/approvals/pending`, {
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setApprovals(data.approvals || []);
            } else {
                setError('Failed to fetch pending approvals');
            }
        } catch (err) {
            setError('Network error fetching approvals');
        } finally {
            setLoading(false);
        }
    };

    const handleDecision = async (approvalId: string, decision: 'approved' | 'rejected') => {
        setDeciding(approvalId);
        try {
            const res = await fetch(`${API_URL}/managerial/approvals/${approvalId}/decide`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ decision })
            });

            if (res.ok) {
                // Remove from list
                setApprovals(prev => prev.filter(a => a.id !== approvalId));
                onDecision?.(decision === 'approved');
            } else {
                const data = await res.json();
                setError(data.detail || 'Failed to process decision');
            }
        } catch (err) {
            setError('Network error processing decision');
        } finally {
            setDeciding(null);
        }
    };

    const getRiskColor = (score: number) => {
        if (score >= 80) return 'text-red-500 bg-red-500/20';
        if (score >= 60) return 'text-orange-500 bg-orange-500/20';
        if (score >= 40) return 'text-yellow-500 bg-yellow-500/20';
        return 'text-green-500 bg-green-500/20';
    };

    const getRiskLabel = (score: number) => {
        if (score >= 80) return 'CRITICAL';
        if (score >= 60) return 'HIGH';
        if (score >= 40) return 'MEDIUM';
        return 'LOW';
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-hidden shadow-2xl animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="p-6 border-b border-slate-700">
                    <h3 className="text-xl font-bold text-red-500 flex items-center gap-2">
                        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        Human Intervention Required
                    </h3>
                    <p className="text-slate-400 text-sm mt-1">
                        {approvals.length} action{approvals.length !== 1 ? 's' : ''} require your approval
                    </p>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto max-h-[50vh]">
                    {error && (
                        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
                            {error}
                            <button onClick={() => setError(null)} className="float-right">✕</button>
                        </div>
                    )}

                    {loading ? (
                        <div className="text-slate-400 text-center py-8">Loading pending approvals...</div>
                    ) : approvals.length === 0 ? (
                        <div className="text-slate-400 text-center py-8">
                            <span className="text-4xl">✓</span>
                            <p className="mt-2">No pending approvals</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {approvals.map((approval) => (
                                <div
                                    key={approval.id}
                                    className="bg-slate-800/50 rounded-lg p-4 border border-slate-700"
                                >
                                    <div className="flex items-start justify-between mb-3">
                                        <div>
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${getRiskColor(approval.risk_score)}`}>
                                                    {getRiskLabel(approval.risk_score)} ({approval.risk_score})
                                                </span>
                                                <span className="text-slate-500 text-xs">
                                                    {approval.agent_name}
                                                </span>
                                            </div>
                                            <h4 className="text-white font-medium">{approval.action_summary}</h4>
                                        </div>
                                        {!approval.is_reversible && (
                                            <span className="text-red-400 text-xs px-2 py-1 bg-red-500/10 rounded">
                                                Irreversible
                                            </span>
                                        )}
                                    </div>

                                    <div className="text-slate-400 text-sm mb-3">
                                        <p><strong>Action:</strong> {approval.action_type}</p>
                                        {approval.resource_type && (
                                            <p><strong>Resource:</strong> {approval.resource_type} {approval.resource_id ? `(${approval.resource_id})` : ''}</p>
                                        )}
                                        <p><strong>Requested by:</strong> {approval.requester_name}</p>
                                        {approval.impact_summary && (
                                            <p><strong>Impact:</strong> {approval.impact_summary}</p>
                                        )}
                                    </div>

                                    <div className="flex gap-2 justify-end">
                                        <button
                                            onClick={() => handleDecision(approval.id, 'rejected')}
                                            disabled={deciding === approval.id}
                                            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-slate-300 transition-colors disabled:opacity-50"
                                        >
                                            {deciding === approval.id ? '...' : 'Reject'}
                                        </button>
                                        <button
                                            onClick={() => handleDecision(approval.id, 'approved')}
                                            disabled={deciding === approval.id}
                                            className="px-4 py-2 rounded-lg bg-green-600 hover:bg-green-700 text-white font-medium transition-colors shadow-lg shadow-green-500/20 disabled:opacity-50"
                                        >
                                            {deciding === approval.id ? '...' : 'Approve'}
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-slate-700 flex justify-between items-center">
                    <button
                        onClick={fetchApprovals}
                        className="text-slate-400 hover:text-white text-sm flex items-center gap-1"
                    >
                        ↻ Refresh
                    </button>
                    <button
                        onClick={onClose}
                        className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}
