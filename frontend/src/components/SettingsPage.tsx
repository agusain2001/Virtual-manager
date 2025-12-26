"use client";

import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';

interface IntegrationStatus {
    connected: boolean;
    email?: string;
    slack_user_id?: string;
    slack_name?: string;
    expired?: boolean;
    error?: string;
    reason?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function SettingsPage() {
    const { isAuthenticated, user } = useAuth();
    const [googleStatus, setGoogleStatus] = useState<IntegrationStatus | null>(null);
    const [slackStatus, setSlackStatus] = useState<IntegrationStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [slackUserId, setSlackUserId] = useState('');
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    useEffect(() => {
        if (isAuthenticated) {
            fetchIntegrationStatus();
        }
    }, [isAuthenticated]);

    // Check URL for success/error params
    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const success = params.get('success');
        const error = params.get('error');

        if (success === 'google_connected') {
            setMessage({ type: 'success', text: 'Google Calendar connected successfully!' });
            // Clear URL params
            window.history.replaceState({}, '', '/settings');
            fetchIntegrationStatus();
        } else if (error) {
            setMessage({ type: 'error', text: `Connection failed: ${error}` });
            window.history.replaceState({}, '', '/settings');
        }
    }, []);

    const fetchIntegrationStatus = async () => {
        try {
            const [googleRes, slackRes] = await Promise.all([
                fetch(`${API_URL}/auth/google/status`, { credentials: 'include' }),
                fetch(`${API_URL}/auth/slack/status`, { credentials: 'include' })
            ]);

            if (googleRes.ok) {
                setGoogleStatus(await googleRes.json());
            }
            if (slackRes.ok) {
                setSlackStatus(await slackRes.json());
            }
        } catch (error) {
            console.error('Error fetching status:', error);
        } finally {
            setLoading(false);
        }
    };

    const connectGoogle = () => {
        window.location.href = `${API_URL}/auth/google/connect`;
    };

    const disconnectGoogle = async () => {
        try {
            const res = await fetch(`${API_URL}/auth/google/disconnect`, {
                method: 'POST',
                credentials: 'include'
            });
            if (res.ok) {
                setGoogleStatus({ connected: false, reason: 'disconnected' });
                setMessage({ type: 'success', text: 'Google Calendar disconnected' });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to disconnect' });
        }
    };

    const linkSlack = async () => {
        if (!slackUserId.trim()) {
            setMessage({ type: 'error', text: 'Please enter your Slack User ID' });
            return;
        }

        try {
            const res = await fetch(`${API_URL}/auth/slack/link`, {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ slack_user_id: slackUserId.trim() })
            });

            if (res.ok) {
                const data = await res.json();
                setSlackStatus({ connected: true, slack_user_id: slackUserId, slack_name: data.slack_name });
                setMessage({ type: 'success', text: `Linked to Slack as ${data.slack_name}` });
                setSlackUserId('');
            } else {
                const error = await res.json();
                setMessage({ type: 'error', text: error.detail || 'Failed to link Slack' });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to link Slack' });
        }
    };

    const unlinkSlack = async () => {
        try {
            const res = await fetch(`${API_URL}/auth/slack/unlink`, {
                method: 'POST',
                credentials: 'include'
            });
            if (res.ok) {
                setSlackStatus({ connected: false, reason: 'unlinked' });
                setMessage({ type: 'success', text: 'Slack unlinked' });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to unlink' });
        }
    };

    const testSlackDM = async () => {
        try {
            const res = await fetch(`${API_URL}/auth/slack/test-dm`, {
                method: 'POST',
                credentials: 'include'
            });
            if (res.ok) {
                setMessage({ type: 'success', text: 'Test message sent! Check your Slack DMs.' });
            } else {
                const error = await res.json();
                setMessage({ type: 'error', text: error.detail || 'Failed to send test message' });
            }
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to send test message' });
        }
    };

    if (!isAuthenticated) {
        return (
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
                <h2 className="text-xl font-bold text-white mb-4">⚙️ Settings</h2>
                <p className="text-slate-400">Please sign in with GitHub to manage your integrations.</p>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-6 border border-slate-700">
                <h2 className="text-xl font-bold text-white mb-6">⚙️ Integration Settings</h2>

                {/* Message Banner */}
                {message && (
                    <div className={`mb-6 p-4 rounded-lg ${message.type === 'success'
                            ? 'bg-green-500/20 border border-green-500/50 text-green-400'
                            : 'bg-red-500/20 border border-red-500/50 text-red-400'
                        }`}>
                        {message.text}
                        <button
                            onClick={() => setMessage(null)}
                            className="float-right text-current opacity-60 hover:opacity-100"
                        >
                            ✕
                        </button>
                    </div>
                )}

                {loading ? (
                    <div className="text-slate-400">Loading integration status...</div>
                ) : (
                    <div className="space-y-6">
                        {/* Google Calendar Integration */}
                        <div className="bg-slate-700/50 rounded-lg p-5 border border-slate-600">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center">
                                        <span className="text-2xl">📅</span>
                                    </div>
                                    <div>
                                        <h3 className="text-white font-semibold">Google Calendar</h3>
                                        <p className="text-slate-400 text-sm">
                                            {googleStatus?.connected
                                                ? `Connected as ${googleStatus.email}`
                                                : 'Connect to sync your calendar'}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {googleStatus?.connected ? (
                                        <>
                                            <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs">
                                                {googleStatus.expired ? '⚠️ Token Expired' : '✓ Connected'}
                                            </span>
                                            <button
                                                onClick={disconnectGoogle}
                                                className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition-colors"
                                            >
                                                Disconnect
                                            </button>
                                        </>
                                    ) : (
                                        <button
                                            onClick={connectGoogle}
                                            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                                        >
                                            <span>Connect</span>
                                        </button>
                                    )}
                                </div>
                            </div>
                            <div className="text-slate-500 text-sm">
                                VAM will read your calendar to find free time and create focus blocks for your tasks.
                            </div>
                        </div>

                        {/* Slack Integration */}
                        <div className="bg-slate-700/50 rounded-lg p-5 border border-slate-600">
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-3">
                                    <div className="w-10 h-10 bg-[#4A154B] rounded-lg flex items-center justify-center">
                                        <span className="text-2xl">💬</span>
                                    </div>
                                    <div>
                                        <h3 className="text-white font-semibold">Slack</h3>
                                        <p className="text-slate-400 text-sm">
                                            {slackStatus?.connected
                                                ? `Linked as ${slackStatus.slack_name || slackStatus.slack_user_id}`
                                                : 'Link your Slack account for standups'}
                                        </p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {slackStatus?.connected ? (
                                        <>
                                            <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded-full text-xs">
                                                ✓ Linked
                                            </span>
                                            <button
                                                onClick={testSlackDM}
                                                className="px-3 py-1.5 bg-purple-500/20 text-purple-400 rounded-lg text-sm hover:bg-purple-500/30 transition-colors"
                                            >
                                                Test DM
                                            </button>
                                            <button
                                                onClick={unlinkSlack}
                                                className="px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg text-sm hover:bg-red-500/30 transition-colors"
                                            >
                                                Unlink
                                            </button>
                                        </>
                                    ) : (
                                        <div className="flex items-center gap-2">
                                            <input
                                                type="text"
                                                value={slackUserId}
                                                onChange={(e) => setSlackUserId(e.target.value)}
                                                placeholder="U12345ABC"
                                                className="px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white text-sm w-32 focus:outline-none focus:border-blue-500"
                                            />
                                            <button
                                                onClick={linkSlack}
                                                className="px-4 py-2 bg-[#4A154B] text-white rounded-lg hover:bg-[#611f69] transition-colors"
                                            >
                                                Link
                                            </button>
                                        </div>
                                    )}
                                </div>
                            </div>
                            <div className="text-slate-500 text-sm">
                                VAM will send you morning standups and notifications via Slack DM.
                                {!slackStatus?.connected && (
                                    <span className="block mt-2 text-slate-400">
                                        To find your Slack User ID: Click your profile → Copy member ID
                                    </span>
                                )}
                            </div>
                        </div>

                        {/* User Info */}
                        <div className="bg-slate-700/50 rounded-lg p-5 border border-slate-600">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-10 h-10 bg-slate-600 rounded-lg flex items-center justify-center">
                                    <span className="text-2xl">👤</span>
                                </div>
                                <div>
                                    <h3 className="text-white font-semibold">Account</h3>
                                    <p className="text-slate-400 text-sm">Signed in via GitHub</p>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                                <div>
                                    <span className="text-slate-500">Username:</span>
                                    <span className="text-white ml-2">{user?.github_username}</span>
                                </div>
                                <div>
                                    <span className="text-slate-500">Default Repo:</span>
                                    <span className="text-white ml-2">{user?.default_repo || 'Not set'}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
