'use client';

import React, { useState, useEffect } from 'react';

interface Employee {
    id: string;
    name: string;
    email: string;
    role: string;
    department?: string;
    timezone: string;
    working_hours: {
        start: string;
        end: string;
    };
    leave_balance: number;
    current_workload_hours: number;
    is_active: boolean;
    skills: {
        name: string;
        proficiency: string;
        years_experience: number;
        is_primary: boolean;
    }[];
}

interface BurnoutRisk {
    employee_name: string;
    risk_level: string;
    risk_score: number;
    recommendation: string;
    is_flagged: boolean;
}

interface LeaveRequest {
    id: string;
    employee_id: string;
    start_date: string;
    end_date: string;
    leave_type: string;
    days_requested: number;
    status: string;
    reason?: string;
    rationale?: string;
}

interface WorkloadData {
    total_active_tasks: number;
    team_members: number;
    workload_distribution: {
        user: string;
        task_count: number;
        estimated_hours: number;
        critical_tasks: number;
        is_overloaded: boolean;
    }[];
    overloaded_members: string[];
    recommendations: string[];
}

const API_BASE = 'http://localhost:8000/api/v1/people';

export function PeopleOpsDashboard() {
    const [activeTab, setActiveTab] = useState<'overview' | 'employees' | 'leaves' | 'meetings'>('overview');
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [workloadData, setWorkloadData] = useState<WorkloadData | null>(null);
    const [burnoutReport, setBurnoutReport] = useState<any>(null);
    const [leaveRequests, setLeaveRequests] = useState<LeaveRequest[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);

            const [employeesRes, workloadRes, burnoutRes, leavesRes] = await Promise.allSettled([
                fetch(`${API_BASE}/employees`),
                fetch(`${API_BASE}/workload/balance`),
                fetch(`${API_BASE}/workload/burnout-risk`),
                fetch(`${API_BASE}/leaves?status=pending`)
            ]);

            if (employeesRes.status === 'fulfilled' && employeesRes.value.ok) {
                setEmployees(await employeesRes.value.json());
            }
            if (workloadRes.status === 'fulfilled' && workloadRes.value.ok) {
                setWorkloadData(await workloadRes.value.json());
            }
            if (burnoutRes.status === 'fulfilled' && burnoutRes.value.ok) {
                setBurnoutReport(await burnoutRes.value.json());
            }
            if (leavesRes.status === 'fulfilled' && leavesRes.value.ok) {
                setLeaveRequests(await leavesRes.value.json());
            }
        } catch (err) {
            setError('Failed to load data');
        } finally {
            setLoading(false);
        }
    };

    const getRiskColor = (level: string) => {
        switch (level) {
            case 'critical': return 'bg-red-500';
            case 'high': return 'bg-orange-500';
            case 'medium': return 'bg-yellow-500';
            default: return 'bg-green-500';
        }
    };

    const getStatusBadge = (status: string) => {
        switch (status) {
            case 'pending': return 'bg-yellow-100 text-yellow-800';
            case 'approved': return 'bg-green-100 text-green-800';
            case 'rejected': return 'bg-red-100 text-red-800';
            default: return 'bg-gray-100 text-gray-800';
        }
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-purple-400"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-6">
            <div className="max-w-7xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div>
                        <h1 className="text-3xl font-bold text-white">People & Operations</h1>
                        <p className="text-purple-300 mt-1">
                            Team management • Workload balance • Leave coordination
                        </p>
                    </div>
                    <button
                        onClick={fetchData}
                        className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Refresh
                    </button>
                </div>

                {/* Tabs */}
                <div className="flex gap-2 bg-slate-800/50 p-1 rounded-lg w-fit">
                    {(['overview', 'employees', 'leaves', 'meetings'] as const).map((tab) => (
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

                {error && (
                    <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-4 text-red-200">
                        {error}
                    </div>
                )}

                {/* Overview Tab */}
                {activeTab === 'overview' && (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* Workload Overview */}
                        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
                            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                                <svg className="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                                Workload Balance
                            </h2>

                            {workloadData && (
                                <>
                                    <div className="grid grid-cols-2 gap-4 mb-4">
                                        <div className="bg-slate-700/50 rounded-lg p-3">
                                            <div className="text-2xl font-bold text-white">{workloadData.total_active_tasks}</div>
                                            <div className="text-sm text-purple-300">Active Tasks</div>
                                        </div>
                                        <div className="bg-slate-700/50 rounded-lg p-3">
                                            <div className="text-2xl font-bold text-white">{workloadData.team_members}</div>
                                            <div className="text-sm text-purple-300">Team Members</div>
                                        </div>
                                    </div>

                                    {workloadData.overloaded_members.length > 0 && (
                                        <div className="bg-orange-500/20 border border-orange-500/50 rounded-lg p-3 mb-4">
                                            <div className="text-orange-300 font-medium">⚠️ Overloaded Members</div>
                                            <div className="text-white text-sm mt-1">
                                                {workloadData.overloaded_members.join(', ')}
                                            </div>
                                        </div>
                                    )}

                                    {workloadData.recommendations.length > 0 && (
                                        <div className="space-y-2">
                                            <div className="text-sm text-purple-300">Recommendations:</div>
                                            {workloadData.recommendations.map((rec, i) => (
                                                <div key={i} className="text-sm text-white bg-slate-700/50 rounded p-2">
                                                    💡 {rec}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>

                        {/* Burnout Risk */}
                        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
                            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                                <svg className="w-5 h-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                                </svg>
                                Burnout Risk Monitor
                            </h2>

                            {burnoutReport && (
                                <>
                                    <div className="grid grid-cols-4 gap-2 mb-4">
                                        {['critical', 'high', 'medium', 'low'].map((level) => (
                                            <div key={level} className="bg-slate-700/50 rounded-lg p-2 text-center">
                                                <div className={`w-3 h-3 rounded-full ${getRiskColor(level)} mx-auto mb-1`}></div>
                                                <div className="text-lg font-bold text-white">
                                                    {burnoutReport.summary?.[level] || 0}
                                                </div>
                                                <div className="text-xs text-purple-300 capitalize">{level}</div>
                                            </div>
                                        ))}
                                    </div>

                                    {burnoutReport.flagged_employees?.length > 0 && (
                                        <div className="space-y-2">
                                            <div className="text-sm text-red-300 font-medium">🚨 Flagged Employees:</div>
                                            {burnoutReport.flagged_employees.map((emp: BurnoutRisk, i: number) => (
                                                <div key={i} className="bg-red-500/20 border border-red-500/30 rounded-lg p-3">
                                                    <div className="flex items-center justify-between">
                                                        <span className="text-white font-medium">{emp.employee_name}</span>
                                                        <span className={`px-2 py-1 rounded text-xs ${getRiskColor(emp.risk_level)} text-white`}>
                                                            {emp.risk_level.toUpperCase()}
                                                        </span>
                                                    </div>
                                                    <div className="text-sm text-red-200 mt-1">{emp.recommendation}</div>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </>
                            )}
                        </div>

                        {/* Pending Leave Requests */}
                        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6 lg:col-span-2">
                            <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                                <svg className="w-5 h-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                                Pending Leave Requests ({leaveRequests.length})
                            </h2>

                            {leaveRequests.length === 0 ? (
                                <div className="text-purple-300 text-center py-4">No pending leave requests</div>
                            ) : (
                                <div className="overflow-x-auto">
                                    <table className="w-full">
                                        <thead>
                                            <tr className="text-left text-purple-300 text-sm border-b border-purple-500/20">
                                                <th className="pb-2">Employee</th>
                                                <th className="pb-2">Type</th>
                                                <th className="pb-2">Dates</th>
                                                <th className="pb-2">Days</th>
                                                <th className="pb-2">Status</th>
                                                <th className="pb-2">Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody className="text-white">
                                            {leaveRequests.map((leave) => (
                                                <tr key={leave.id} className="border-b border-purple-500/10">
                                                    <td className="py-3">{leave.employee_id}</td>
                                                    <td className="py-3 capitalize">{leave.leave_type}</td>
                                                    <td className="py-3 text-sm">
                                                        {new Date(leave.start_date).toLocaleDateString()} - {new Date(leave.end_date).toLocaleDateString()}
                                                    </td>
                                                    <td className="py-3">{leave.days_requested}</td>
                                                    <td className="py-3">
                                                        <span className={`px-2 py-1 rounded-full text-xs ${getStatusBadge(leave.status)}`}>
                                                            {leave.status}
                                                        </span>
                                                    </td>
                                                    <td className="py-3">
                                                        <div className="flex gap-2">
                                                            <button className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white text-xs rounded">
                                                                Approve
                                                            </button>
                                                            <button className="px-2 py-1 bg-red-600 hover:bg-red-700 text-white text-xs rounded">
                                                                Reject
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Employees Tab */}
                {activeTab === 'employees' && (
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-semibold text-white">Team Members</h2>
                            <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm">
                                + Add Employee
                            </button>
                        </div>

                        {employees.length === 0 ? (
                            <div className="text-purple-300 text-center py-8">
                                No employees found. Add your first team member.
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                {employees.map((employee) => (
                                    <div key={employee.id} className="bg-slate-700/50 rounded-lg p-4 hover:bg-slate-700/70 transition-colors">
                                        <div className="flex items-start justify-between">
                                            <div>
                                                <h3 className="text-white font-medium">{employee.name}</h3>
                                                <p className="text-purple-300 text-sm">{employee.role}</p>
                                                {employee.department && (
                                                    <p className="text-purple-400 text-xs">{employee.department}</p>
                                                )}
                                            </div>
                                            <div className={`w-2 h-2 rounded-full ${employee.is_active ? 'bg-green-400' : 'bg-gray-400'}`}></div>
                                        </div>

                                        <div className="mt-3 pt-3 border-t border-purple-500/20 space-y-2 text-sm">
                                            <div className="flex justify-between text-purple-300">
                                                <span>Workload</span>
                                                <span className="text-white">{employee.current_workload_hours}h</span>
                                            </div>
                                            <div className="flex justify-between text-purple-300">
                                                <span>Leave Balance</span>
                                                <span className="text-white">{employee.leave_balance} days</span>
                                            </div>
                                            <div className="flex justify-between text-purple-300">
                                                <span>Timezone</span>
                                                <span className="text-white">{employee.timezone}</span>
                                            </div>
                                        </div>

                                        {employee.skills && employee.skills.length > 0 && (
                                            <div className="mt-3 flex flex-wrap gap-1">
                                                {employee.skills.slice(0, 3).map((skill, i) => (
                                                    <span key={i} className="px-2 py-0.5 bg-purple-600/30 text-purple-200 text-xs rounded">
                                                        {skill.name}
                                                    </span>
                                                ))}
                                                {employee.skills.length > 3 && (
                                                    <span className="px-2 py-0.5 bg-purple-600/30 text-purple-200 text-xs rounded">
                                                        +{employee.skills.length - 3}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {/* Leaves Tab */}
                {activeTab === 'leaves' && (
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-semibold text-white">Leave Management</h2>
                            <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm">
                                + New Request
                            </button>
                        </div>

                        <div className="text-purple-300 text-center py-8">
                            Leave management interface - view all leave requests, approvals, and calendar
                        </div>
                    </div>
                )}

                {/* Meetings Tab */}
                {activeTab === 'meetings' && (
                    <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-6">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-semibold text-white">Meeting Scheduler</h2>
                            <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm">
                                + Schedule Meeting
                            </button>
                        </div>

                        <div className="text-purple-300 text-center py-8">
                            Meeting scheduler interface - upcoming meetings, conflict detection, time suggestions
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default PeopleOpsDashboard;
