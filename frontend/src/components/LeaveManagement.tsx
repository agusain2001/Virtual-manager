'use client';

import React, { useState, useEffect } from 'react';

interface LeaveRequest {
    id: string;
    employee_id: string;
    start_date: string;
    end_date: string;
    leave_type: string;
    days_requested: number;
    status: string;
    reason?: string;
    has_delivery_impact: boolean;
    reviewed_by?: string;
    rationale?: string;
}

interface Employee {
    id: string;
    name: string;
    email: string;
}

interface Props {
    refreshKey?: number;
}

const API_BASE = 'http://localhost:8000/api/v1/people';

export function LeaveManagement({ refreshKey = 0 }: Props) {
    const [leaves, setLeaves] = useState<LeaveRequest[]>([]);
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeFilter, setActiveFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
    const [showNewRequest, setShowNewRequest] = useState(false);
    const [approvalModal, setApprovalModal] = useState<{ leave: LeaveRequest; action: 'approve' | 'reject' } | null>(null);

    const [newRequest, setNewRequest] = useState({
        employee_id: '',
        start_date: '',
        end_date: '',
        leave_type: 'vacation',
        reason: ''
    });

    const [approvalData, setApprovalData] = useState({
        reviewed_by: 'Manager',
        rationale: '',
        coverage_plan: '',
        suggested_alternative: ''
    });

    useEffect(() => {
        fetchData();
    }, [refreshKey]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [leavesRes, employeesRes] = await Promise.all([
                fetch(`${API_BASE}/leaves`),
                fetch(`${API_BASE}/employees`)
            ]);

            if (leavesRes.ok) setLeaves(await leavesRes.json());
            if (employeesRes.ok) setEmployees(await employeesRes.json());
        } catch (err) {
            console.error('Failed to fetch data:', err);
        } finally {
            setLoading(false);
        }
    };

    const submitLeaveRequest = async () => {
        try {
            const response = await fetch(`${API_BASE}/leaves`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...newRequest,
                    start_date: new Date(newRequest.start_date).toISOString(),
                    end_date: new Date(newRequest.end_date).toISOString()
                })
            });

            if (response.ok) {
                setShowNewRequest(false);
                setNewRequest({ employee_id: '', start_date: '', end_date: '', leave_type: 'vacation', reason: '' });
                fetchData();
            }
        } catch (err) {
            console.error('Failed to submit leave request:', err);
        }
    };

    const handleApproval = async () => {
        if (!approvalModal) return;

        const endpoint = approvalModal.action === 'approve' ? 'approve' : 'reject';
        const body = approvalModal.action === 'approve'
            ? {
                reviewed_by: approvalData.reviewed_by,
                rationale: approvalData.rationale,
                coverage_plan: approvalData.coverage_plan
            }
            : {
                reviewed_by: approvalData.reviewed_by,
                rationale: approvalData.rationale,
                suggested_alternative: approvalData.suggested_alternative
            };

        try {
            const response = await fetch(`${API_BASE}/leaves/${approvalModal.leave.id}/${endpoint}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });

            if (response.ok) {
                setApprovalModal(null);
                setApprovalData({ reviewed_by: 'Manager', rationale: '', coverage_plan: '', suggested_alternative: '' });
                fetchData();
            }
        } catch (err) {
            console.error('Failed to process approval:', err);
        }
    };

    const filteredLeaves = leaves.filter(leave => {
        if (activeFilter === 'all') return true;
        return leave.status === activeFilter;
    });

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'pending': return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
            case 'approved': return 'bg-green-500/20 text-green-300 border-green-500/30';
            case 'rejected': return 'bg-red-500/20 text-red-300 border-red-500/30';
            default: return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
        }
    };

    const getLeaveTypeIcon = (type: string) => {
        switch (type) {
            case 'vacation': return '🏖️';
            case 'sick': return '🏥';
            case 'personal': return '👤';
            case 'emergency': return '🚨';
            default: return '📅';
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-purple-400"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-white">Leave Management</h2>
                    <p className="text-purple-300 text-sm mt-1">
                        All decisions include rationale • Default to approval unless business risk exists
                    </p>
                </div>
                <button
                    onClick={() => setShowNewRequest(true)}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    New Request
                </button>
            </div>

            {/* Filters */}
            <div className="flex gap-2">
                {(['all', 'pending', 'approved', 'rejected'] as const).map((filter) => (
                    <button
                        key={filter}
                        onClick={() => setActiveFilter(filter)}
                        className={`px-4 py-2 rounded-lg text-sm capitalize transition-colors ${activeFilter === filter
                                ? 'bg-purple-600 text-white'
                                : 'bg-slate-700/50 text-purple-300 hover:bg-slate-700'
                            }`}
                    >
                        {filter}
                        {filter !== 'all' && (
                            <span className="ml-2 px-1.5 py-0.5 bg-slate-600 rounded text-xs">
                                {leaves.filter(l => l.status === filter).length}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* Leave Requests List */}
            <div className="space-y-4">
                {filteredLeaves.length === 0 ? (
                    <div className="text-center py-12 text-purple-300">
                        No leave requests found
                    </div>
                ) : (
                    filteredLeaves.map((leave) => (
                        <div
                            key={leave.id}
                            className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-5 hover:border-purple-500/40 transition-colors"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex gap-4">
                                    <div className="text-3xl">{getLeaveTypeIcon(leave.leave_type)}</div>
                                    <div>
                                        <div className="flex items-center gap-3">
                                            <h3 className="text-lg font-medium text-white capitalize">
                                                {leave.leave_type} Leave
                                            </h3>
                                            <span className={`px-2 py-0.5 rounded-full text-xs border ${getStatusBadge(leave.status)}`}>
                                                {leave.status}
                                            </span>
                                            {leave.has_delivery_impact && (
                                                <span className="px-2 py-0.5 rounded-full text-xs bg-orange-500/20 text-orange-300 border border-orange-500/30">
                                                    ⚠️ Delivery Impact
                                                </span>
                                            )}
                                        </div>
                                        <p className="text-purple-300 text-sm mt-1">
                                            {new Date(leave.start_date).toLocaleDateString()} – {new Date(leave.end_date).toLocaleDateString()}
                                            <span className="mx-2">•</span>
                                            {leave.days_requested} days
                                        </p>
                                        {leave.reason && (
                                            <p className="text-purple-400 text-sm mt-2">{leave.reason}</p>
                                        )}
                                        {leave.rationale && (
                                            <p className="text-green-300 text-sm mt-2 bg-green-500/10 p-2 rounded">
                                                <strong>Decision Rationale:</strong> {leave.rationale}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                {leave.status === 'pending' && (
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => setApprovalModal({ leave, action: 'approve' })}
                                            className="px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg transition-colors"
                                        >
                                            Approve
                                        </button>
                                        <button
                                            onClick={() => setApprovalModal({ leave, action: 'reject' })}
                                            className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors"
                                        >
                                            Reject
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* New Request Modal */}
            {showNewRequest && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-slate-800 rounded-xl border border-purple-500/30 p-6 w-full max-w-md">
                        <h3 className="text-xl font-semibold text-white mb-4">Submit Leave Request</h3>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-purple-300 text-sm mb-1">Employee</label>
                                <select
                                    value={newRequest.employee_id}
                                    onChange={(e) => setNewRequest({ ...newRequest, employee_id: e.target.value })}
                                    className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                >
                                    <option value="">Select employee...</option>
                                    {employees.map((emp) => (
                                        <option key={emp.id} value={emp.id}>{emp.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Start Date</label>
                                    <input
                                        type="date"
                                        value={newRequest.start_date}
                                        onChange={(e) => setNewRequest({ ...newRequest, start_date: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                    />
                                </div>
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">End Date</label>
                                    <input
                                        type="date"
                                        value={newRequest.end_date}
                                        onChange={(e) => setNewRequest({ ...newRequest, end_date: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-purple-300 text-sm mb-1">Leave Type</label>
                                <select
                                    value={newRequest.leave_type}
                                    onChange={(e) => setNewRequest({ ...newRequest, leave_type: e.target.value })}
                                    className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                >
                                    <option value="vacation">🏖️ Vacation</option>
                                    <option value="sick">🏥 Sick Leave</option>
                                    <option value="personal">👤 Personal</option>
                                    <option value="emergency">🚨 Emergency</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-purple-300 text-sm mb-1">Reason (optional)</label>
                                <textarea
                                    value={newRequest.reason}
                                    onChange={(e) => setNewRequest({ ...newRequest, reason: e.target.value })}
                                    rows={3}
                                    className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500 resize-none"
                                    placeholder="Brief reason for leave..."
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setShowNewRequest(false)}
                                className="px-4 py-2 text-purple-300 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={submitLeaveRequest}
                                disabled={!newRequest.employee_id || !newRequest.start_date || !newRequest.end_date}
                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white rounded-lg transition-colors"
                            >
                                Submit Request
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Approval Modal */}
            {approvalModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="bg-slate-800 rounded-xl border border-purple-500/30 p-6 w-full max-w-md">
                        <h3 className="text-xl font-semibold text-white mb-2">
                            {approvalModal.action === 'approve' ? '✅ Approve' : '❌ Reject'} Leave Request
                        </h3>
                        <p className="text-purple-300 text-sm mb-4">
                            All decisions must include a rationale (required).
                        </p>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-purple-300 text-sm mb-1">Reviewed By</label>
                                <input
                                    type="text"
                                    value={approvalData.reviewed_by}
                                    onChange={(e) => setApprovalData({ ...approvalData, reviewed_by: e.target.value })}
                                    className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                />
                            </div>

                            <div>
                                <label className="block text-purple-300 text-sm mb-1">Rationale *</label>
                                <textarea
                                    value={approvalData.rationale}
                                    onChange={(e) => setApprovalData({ ...approvalData, rationale: e.target.value })}
                                    rows={3}
                                    className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500 resize-none"
                                    placeholder={approvalModal.action === 'approve'
                                        ? "Explain approval decision..."
                                        : "Explain rejection reason..."
                                    }
                                />
                            </div>

                            {approvalModal.action === 'approve' ? (
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Coverage Plan (optional)</label>
                                    <input
                                        type="text"
                                        value={approvalData.coverage_plan}
                                        onChange={(e) => setApprovalData({ ...approvalData, coverage_plan: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                        placeholder="Who will cover responsibilities?"
                                    />
                                </div>
                            ) : (
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Suggested Alternative</label>
                                    <input
                                        type="text"
                                        value={approvalData.suggested_alternative}
                                        onChange={(e) => setApprovalData({ ...approvalData, suggested_alternative: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                        placeholder="Alternative dates or options..."
                                    />
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setApprovalModal(null)}
                                className="px-4 py-2 text-purple-300 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleApproval}
                                disabled={!approvalData.rationale}
                                className={`px-4 py-2 rounded-lg transition-colors ${approvalModal.action === 'approve'
                                        ? 'bg-green-600 hover:bg-green-700 disabled:bg-green-600/50'
                                        : 'bg-red-600 hover:bg-red-700 disabled:bg-red-600/50'
                                    } text-white`}
                            >
                                {approvalModal.action === 'approve' ? 'Approve' : 'Reject'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default LeaveManagement;
