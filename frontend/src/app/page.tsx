'use client';

import { useState, useEffect } from 'react';
import { AgentActivityLog } from '@/components/AgentActivityLog';
import TaskList from '@/components/TaskList';
import { ProjectList } from '@/components/ProjectList';
import CreateTaskModal from '@/components/CreateTaskModal';
import CreateProjectModal from '@/components/CreateProjectModal';
import DashboardStats from '@/components/DashboardStats';

type View = 'overview' | 'tasks' | 'projects';

export default function Dashboard() {
  const [currentView, setCurrentView] = useState<View>('overview');
  const [isTaskModalOpen, setIsTaskModalOpen] = useState(false);
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-xl border-b border-slate-700/50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 via-purple-400 to-pink-400 bg-clip-text text-transparent">
                Virtual AI Manager
              </h1>
              <p className="text-slate-400 text-sm mt-1">Autonomous Task & Project Orchestration</p>
            </div>

            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-400 px-4 py-2 rounded-full border border-emerald-500/30 shadow-lg shadow-emerald-500/10">
                <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium">System Online</span>
              </div>

              <button
                onClick={() => setIsProjectModalOpen(true)}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium transition-all shadow-lg shadow-purple-600/20 hover:shadow-purple-600/40"
              >
                + New Project
              </button>

              <button
                onClick={() => setIsTaskModalOpen(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-all shadow-lg shadow-blue-600/20 hover:shadow-blue-600/40"
              >
                + New Task
              </button>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex gap-2 mt-4">
            <button
              onClick={() => setCurrentView('overview')}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${currentView === 'overview'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
            >
              Overview
            </button>
            <button
              onClick={() => setCurrentView('tasks')}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${currentView === 'tasks'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
            >
              Tasks
            </button>
            <button
              onClick={() => setCurrentView('projects')}
              className={`px-4 py-2 rounded-lg font-medium transition-all ${currentView === 'projects'
                ? 'bg-blue-600 text-white shadow-lg'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
                }`}
            >
              Projects
            </button>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-8">
        {currentView === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Stats */}
            <div className="lg:col-span-3">
              <DashboardStats refreshKey={refreshKey} />
            </div>

            {/* Projects Overview */}
            <div className="lg:col-span-1">
              <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold text-blue-300">Active Projects</h2>
                  <button
                    onClick={() => setCurrentView('projects')}
                    className="text-sm text-slate-400 hover:text-blue-400"
                  >
                    View all →
                  </button>
                </div>
                <ProjectList limit={5} refreshKey={refreshKey} />
              </div>
            </div>

            {/* Recent Tasks */}
            <div className="lg:col-span-2">
              <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-xl font-bold text-blue-300">Recent Tasks</h2>
                  <button
                    onClick={() => setCurrentView('tasks')}
                    className="text-sm text-slate-400 hover:text-blue-400"
                  >
                    View all →
                  </button>
                </div>
                <TaskList limit={8} refreshKey={refreshKey} />
              </div>
            </div>

            {/* Activity Feed */}
            <div className="lg:col-span-3">
              <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl shadow-2xl overflow-hidden">
                <div className="p-6 border-b border-slate-700/50">
                  <h2 className="text-xl font-bold text-blue-300">Live Agent Activity</h2>
                </div>
                <AgentActivityLog />
              </div>
            </div>
          </div>
        )}

        {currentView === 'tasks' && (
          <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-blue-300">All Tasks</h2>
              <button
                onClick={handleRefresh}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-all"
              >
                Refresh
              </button>
            </div>
            <TaskList refreshKey={refreshKey} />
          </div>
        )}

        {currentView === 'projects' && (
          <div className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-6 shadow-2xl">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold text-blue-300">All Projects</h2>
              <button
                onClick={handleRefresh}
                className="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg transition-all"
              >
                Refresh
              </button>
            </div>
            <ProjectList refreshKey={refreshKey} />
          </div>
        )}
      </div>

      {/* Modals */}
      <CreateTaskModal
        isOpen={isTaskModalOpen}
        onClose={() => setIsTaskModalOpen(false)}
        onSuccess={handleRefresh}
      />

      <CreateProjectModal
        isOpen={isProjectModalOpen}
        onClose={() => setIsProjectModalOpen(false)}
        onSuccess={handleRefresh}
      />
    </main>
  );
}