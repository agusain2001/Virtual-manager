"use client";

import React, { useState, useEffect } from 'react';
import DashboardStats from '@/components/DashboardStats';
import TaskList from '@/components/TaskList';
import ProjectList from '@/components/ProjectList';
import { AgentActivityLog } from '@/components/AgentActivityLog';
import ManagerialDashboard from '@/components/ManagerialDashboard';
import GoalTracker from '@/components/GoalTracker';
import ExecutionDashboard from '@/components/ExecutionDashboard';
import EscalationAlerts from '@/components/EscalationAlerts';
import ProjectHealthDashboard from '@/components/ProjectHealthDashboard';
import LoginButton from '@/components/LoginButton';
import RepoSelector from '@/components/RepoSelector';
import { useAuth } from '@/components/AuthContext';

type TabType = 'overview' | 'tasks' | 'projects' | 'execution' | 'goals' | 'managerial';

export default function VAMDashboard() {
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [refreshKey, setRefreshKey] = useState(0);
    const { isAuthenticated, user } = useAuth();

    const handleRefresh = () => {
        setRefreshKey(prev => prev + 1);
    };

    const tabs = [
        { id: 'overview', label: 'Overview', icon: '📊' },
        { id: 'tasks', label: 'Tasks', icon: '✅' },
        { id: 'projects', label: 'Projects', icon: '📁' },
        { id: 'execution', label: 'Execution', icon: '🔄' },
        { id: 'goals', label: 'Goals', icon: '🎯' },
        { id: 'managerial', label: 'AI Manager', icon: '🤖' },
    ];

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
            {/* Header */}
            <header className="bg-slate-800/50 backdrop-blur-lg border-b border-slate-700 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-xl">
                                V
                            </div>
                            <div>
                                <h1 className="text-xl font-bold text-white">Virtual AI Manager</h1>
                                <p className="text-slate-400 text-sm">Autonomous Project Management System</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-4">
                            {/* GitHub Repo Selector - only show when authenticated */}
                            {isAuthenticated && <RepoSelector />}

                            <button
                                onClick={handleRefresh}
                                className="p-2 hover:bg-slate-700 rounded-lg transition-colors text-slate-400 hover:text-white"
                                title="Refresh Data"
                            >
                                🔄
                            </button>
                            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
                            <span className="text-green-400 text-sm font-medium">System Online</span>

                            {/* Divider */}
                            <div className="w-px h-8 bg-slate-600"></div>

                            {/* Login Button */}
                            <LoginButton />
                        </div>
                    </div>
                </div>
            </header>

            {/* Navigation Tabs */}
            <nav className="bg-slate-800/30 border-b border-slate-700">
                <div className="max-w-7xl mx-auto px-4">
                    <div className="flex gap-1 overflow-x-auto py-2">
                        {tabs.map((tab) => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id as TabType)}
                                className={`px-4 py-2 rounded-lg font-medium transition-all whitespace-nowrap ${activeTab === tab.id
                                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
                                    : 'text-slate-400 hover:text-white hover:bg-slate-700'
                                    }`}
                            >
                                <span className="mr-2">{tab.icon}</span>
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 py-6">
                {/* Overview Tab */}
                {activeTab === 'overview' && (
                    <div className="space-y-6">
                        {/* Stats Row */}
                        <DashboardStats />

                        {/* Two Column Layout */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            {/* Left Column */}
                            <div className="space-y-6">
                                <EscalationAlerts />
                                <ProjectHealthDashboard />
                            </div>

                            {/* Right Column */}
                            <div className="space-y-6">
                                <AgentActivityLog limit={10} refreshKey={refreshKey} />
                            </div>
                        </div>
                    </div>
                )}

                {/* Tasks Tab */}
                {activeTab === 'tasks' && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="lg:col-span-2">
                                <TaskList />
                            </div>
                            <div>
                                <ExecutionDashboard />
                            </div>
                        </div>
                    </div>
                )}

                {/* Projects Tab */}
                {activeTab === 'projects' && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <div className="lg:col-span-2">
                                <ProjectList />
                            </div>
                            <div>
                                <ProjectHealthDashboard />
                            </div>
                        </div>
                    </div>
                )}

                {/* Execution Tab */}
                {activeTab === 'execution' && (
                    <div className="space-y-6">
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                            <ExecutionDashboard />
                            <EscalationAlerts />
                        </div>
                        <AgentActivityLog limit={20} refreshKey={refreshKey} />
                    </div>
                )}

                {/* Goals Tab */}
                {activeTab === 'goals' && (
                    <div className="space-y-6">
                        <GoalTracker />
                    </div>
                )}

                {/* Managerial Tab */}
                {activeTab === 'managerial' && (
                    <div className="space-y-6">
                        <ManagerialDashboard />
                    </div>
                )}
            </main>

            {/* Footer */}
            <footer className="bg-slate-800/30 border-t border-slate-700 mt-8">
                <div className="max-w-7xl mx-auto px-4 py-4">
                    <div className="flex justify-between items-center text-slate-500 text-sm">
                        <span>Virtual AI Manager v1.0.0</span>
                        <span>Powered by AI Agents</span>
                    </div>
                </div>
            </footer>
        </div>
    );
}
