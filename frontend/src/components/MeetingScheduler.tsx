'use client';

import React, { useState, useEffect } from 'react';

interface Meeting {
    id: string;
    title: string;
    organizer: string;
    start_time: string;
    end_time: string;
    status: string;
    description?: string;
    location?: string;
}

interface Employee {
    id: string;
    name: string;
    email: string;
}

interface TimeSuggestion {
    start_time: string;
    end_time: string;
    all_available: boolean;
    score?: number;
}

interface Props {
    refreshKey?: number;
}

const API_BASE = 'http://localhost:8000/api/v1/people';

export function MeetingScheduler({ refreshKey = 0 }: Props) {
    const [meetings, setMeetings] = useState<Meeting[]>([]);
    const [employees, setEmployees] = useState<Employee[]>([]);
    const [loading, setLoading] = useState(true);
    const [showScheduler, setShowScheduler] = useState(false);
    const [timeSuggestions, setTimeSuggestions] = useState<TimeSuggestion[]>([]);
    const [loadingSuggestions, setLoadingSuggestions] = useState(false);

    const [newMeeting, setNewMeeting] = useState({
        title: '',
        organizer: '',
        participant_ids: [] as string[],
        start_time: '',
        end_time: '',
        description: '',
        location: ''
    });

    useEffect(() => {
        fetchData();
    }, [refreshKey]);

    const fetchData = async () => {
        try {
            setLoading(true);
            const [meetingsRes, employeesRes] = await Promise.all([
                fetch(`${API_BASE}/meetings`),
                fetch(`${API_BASE}/employees`)
            ]);

            if (meetingsRes.ok) setMeetings(await meetingsRes.json());
            if (employeesRes.ok) setEmployees(await employeesRes.json());
        } catch (err) {
            console.error('Failed to fetch data:', err);
        } finally {
            setLoading(false);
        }
    };

    const fetchTimeSuggestions = async () => {
        if (newMeeting.participant_ids.length === 0) return;

        setLoadingSuggestions(true);
        try {
            const response = await fetch(`${API_BASE}/meetings/suggest-times`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    participant_ids: newMeeting.participant_ids,
                    duration_minutes: 60,
                    search_days: 7
                })
            });

            if (response.ok) {
                setTimeSuggestions(await response.json());
            }
        } catch (err) {
            console.error('Failed to get suggestions:', err);
        } finally {
            setLoadingSuggestions(false);
        }
    };

    const scheduleMeeting = async () => {
        try {
            const response = await fetch(`${API_BASE}/meetings`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ...newMeeting,
                    start_time: new Date(newMeeting.start_time).toISOString(),
                    end_time: new Date(newMeeting.end_time).toISOString()
                })
            });

            if (response.ok) {
                setShowScheduler(false);
                setNewMeeting({
                    title: '',
                    organizer: '',
                    participant_ids: [],
                    start_time: '',
                    end_time: '',
                    description: '',
                    location: ''
                });
                setTimeSuggestions([]);
                fetchData();
            }
        } catch (err) {
            console.error('Failed to schedule meeting:', err);
        }
    };

    const toggleParticipant = (employeeId: string) => {
        setNewMeeting(prev => ({
            ...prev,
            participant_ids: prev.participant_ids.includes(employeeId)
                ? prev.participant_ids.filter(id => id !== employeeId)
                : [...prev.participant_ids, employeeId]
        }));
    };

    const applyTimeSuggestion = (suggestion: TimeSuggestion) => {
        const start = new Date(suggestion.start_time);
        const end = new Date(suggestion.end_time);

        setNewMeeting(prev => ({
            ...prev,
            start_time: start.toISOString().slice(0, 16),
            end_time: end.toISOString().slice(0, 16)
        }));
    };

    const formatDateTime = (iso: string) => {
        const date = new Date(iso);
        return date.toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        });
    };

    const formatDuration = (start: string, end: string) => {
        const startDate = new Date(start);
        const endDate = new Date(end);
        const minutes = (endDate.getTime() - startDate.getTime()) / (1000 * 60);
        return minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes}m`;
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
                    <h2 className="text-2xl font-bold text-white">Meeting Scheduler</h2>
                    <p className="text-purple-300 text-sm mt-1">
                        Smart scheduling • Conflict detection • Time zone aware
                    </p>
                </div>
                <button
                    onClick={() => setShowScheduler(true)}
                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors flex items-center gap-2"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    Schedule Meeting
                </button>
            </div>

            {/* Upcoming Meetings */}
            <div className="grid gap-4">
                {meetings.length === 0 ? (
                    <div className="text-center py-12 text-purple-300 bg-slate-800/50 rounded-xl border border-purple-500/20">
                        No upcoming meetings scheduled
                    </div>
                ) : (
                    meetings.map((meeting) => (
                        <div
                            key={meeting.id}
                            className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-purple-500/20 p-5 hover:border-purple-500/40 transition-colors"
                        >
                            <div className="flex items-start justify-between">
                                <div className="flex gap-4">
                                    <div className="w-12 h-12 bg-purple-600/30 rounded-lg flex items-center justify-center">
                                        <svg className="w-6 h-6 text-purple-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                        </svg>
                                    </div>
                                    <div>
                                        <h3 className="text-lg font-medium text-white">{meeting.title}</h3>
                                        <p className="text-purple-300 text-sm mt-1">
                                            {formatDateTime(meeting.start_time)}
                                            <span className="mx-2">•</span>
                                            {formatDuration(meeting.start_time, meeting.end_time)}
                                        </p>
                                        <p className="text-purple-400 text-sm mt-1">
                                            Organized by {meeting.organizer}
                                            {meeting.location && <span> • {meeting.location}</span>}
                                        </p>
                                    </div>
                                </div>

                                <span className="px-2 py-1 bg-green-500/20 text-green-300 text-xs rounded-full border border-green-500/30">
                                    {meeting.status}
                                </span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Schedule Meeting Modal */}
            {showScheduler && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 overflow-y-auto py-8">
                    <div className="bg-slate-800 rounded-xl border border-purple-500/30 p-6 w-full max-w-2xl mx-4">
                        <h3 className="text-xl font-semibold text-white mb-4">Schedule New Meeting</h3>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Meeting Title</label>
                                    <input
                                        type="text"
                                        value={newMeeting.title}
                                        onChange={(e) => setNewMeeting({ ...newMeeting, title: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                        placeholder="Weekly standup..."
                                    />
                                </div>

                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Organizer</label>
                                    <select
                                        value={newMeeting.organizer}
                                        onChange={(e) => setNewMeeting({ ...newMeeting, organizer: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                    >
                                        <option value="">Select organizer...</option>
                                        {employees.map((emp) => (
                                            <option key={emp.id} value={emp.name}>{emp.name}</option>
                                        ))}
                                    </select>
                                </div>

                                <div>
                                    <label className="block text-purple-300 text-sm mb-2">
                                        Participants ({newMeeting.participant_ids.length} selected)
                                    </label>
                                    <div className="max-h-40 overflow-y-auto bg-slate-700/50 rounded-lg p-2 space-y-1">
                                        {employees.map((emp) => (
                                            <label
                                                key={emp.id}
                                                className={`flex items-center gap-2 p-2 rounded cursor-pointer transition-colors ${newMeeting.participant_ids.includes(emp.id)
                                                        ? 'bg-purple-600/30 text-white'
                                                        : 'text-purple-300 hover:bg-slate-600/50'
                                                    }`}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={newMeeting.participant_ids.includes(emp.id)}
                                                    onChange={() => toggleParticipant(emp.id)}
                                                    className="rounded border-purple-500"
                                                />
                                                {emp.name}
                                            </label>
                                        ))}
                                    </div>
                                    <button
                                        onClick={fetchTimeSuggestions}
                                        disabled={newMeeting.participant_ids.length === 0 || loadingSuggestions}
                                        className="mt-2 w-full px-3 py-2 bg-purple-600/30 hover:bg-purple-600/50 disabled:opacity-50 text-purple-200 rounded-lg text-sm transition-colors"
                                    >
                                        {loadingSuggestions ? 'Finding times...' : '✨ Find optimal times'}
                                    </button>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-purple-300 text-sm mb-1">Start Time</label>
                                        <input
                                            type="datetime-local"
                                            value={newMeeting.start_time}
                                            onChange={(e) => setNewMeeting({ ...newMeeting, start_time: e.target.value })}
                                            className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-purple-300 text-sm mb-1">End Time</label>
                                        <input
                                            type="datetime-local"
                                            value={newMeeting.end_time}
                                            onChange={(e) => setNewMeeting({ ...newMeeting, end_time: e.target.value })}
                                            className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Location (optional)</label>
                                    <input
                                        type="text"
                                        value={newMeeting.location}
                                        onChange={(e) => setNewMeeting({ ...newMeeting, location: e.target.value })}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500"
                                        placeholder="Room A / Zoom link..."
                                    />
                                </div>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-purple-300 text-sm mb-1">Description (optional)</label>
                                    <textarea
                                        value={newMeeting.description}
                                        onChange={(e) => setNewMeeting({ ...newMeeting, description: e.target.value })}
                                        rows={3}
                                        className="w-full px-3 py-2 bg-slate-700 border border-purple-500/30 rounded-lg text-white focus:outline-none focus:border-purple-500 resize-none"
                                        placeholder="Meeting agenda..."
                                    />
                                </div>

                                {timeSuggestions.length > 0 && (
                                    <div>
                                        <label className="block text-purple-300 text-sm mb-2">
                                            ✨ Optimal Time Suggestions
                                        </label>
                                        <div className="space-y-2 max-h-60 overflow-y-auto">
                                            {timeSuggestions.map((suggestion, i) => (
                                                <button
                                                    key={i}
                                                    onClick={() => applyTimeSuggestion(suggestion)}
                                                    className="w-full text-left p-3 bg-green-500/10 hover:bg-green-500/20 border border-green-500/30 rounded-lg transition-colors"
                                                >
                                                    <div className="text-white text-sm font-medium">
                                                        {new Date(suggestion.start_time).toLocaleString('en-US', {
                                                            weekday: 'short',
                                                            month: 'short',
                                                            day: 'numeric',
                                                            hour: 'numeric',
                                                            minute: '2-digit',
                                                            hour12: true
                                                        })}
                                                    </div>
                                                    <div className="text-green-300 text-xs mt-1 flex items-center gap-2">
                                                        <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                                                        All participants available
                                                    </div>
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="flex justify-end gap-3 mt-6 pt-4 border-t border-purple-500/20">
                            <button
                                onClick={() => {
                                    setShowScheduler(false);
                                    setTimeSuggestions([]);
                                }}
                                className="px-4 py-2 text-purple-300 hover:text-white transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={scheduleMeeting}
                                disabled={!newMeeting.title || !newMeeting.organizer || !newMeeting.start_time || !newMeeting.end_time}
                                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-600/50 text-white rounded-lg transition-colors"
                            >
                                Schedule Meeting
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default MeetingScheduler;
