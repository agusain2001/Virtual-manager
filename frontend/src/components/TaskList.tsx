'use client';

import { useEffect, useState } from 'react';
import { useAuth } from './AuthContext';

type Task = {
  id: string;
  name: string;
  project_id: string;
  owner: string;
  priority: string;
  status: string;
  deadline: string | null;
  created_at: string;
  // GitHub Integration fields
  github_issue_number?: number;
  github_repo?: string;
  github_sync_status?: string;
  github_issue_url?: string;
};

const statusColors: Record<string, string> = {
  not_started: 'bg-slate-600 text-slate-200',
  in_progress: 'bg-blue-600 text-blue-100',
  blocked: 'bg-red-600 text-red-100',
  completed: 'bg-green-600 text-green-100',
  cancelled: 'bg-gray-600 text-gray-200',
};

const priorityColors: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-green-400',
};

const syncStatusColors: Record<string, { bg: string; text: string; icon: string }> = {
  not_synced: { bg: 'bg-slate-600', text: 'text-slate-300', icon: '○' },
  syncing: { bg: 'bg-yellow-600', text: 'text-yellow-100', icon: '↻' },
  synced: { bg: 'bg-green-600', text: 'text-green-100', icon: '✓' },
  error: { bg: 'bg-red-600', text: 'text-red-100', icon: '✗' },
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function TaskList({ limit, refreshKey }: { limit?: number; refreshKey?: number }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [syncingTasks, setSyncingTasks] = useState<Set<string>>(new Set());
  const { user, isAuthenticated } = useAuth();

  useEffect(() => {
    fetchTasks();
  }, [refreshKey, selectedStatus]);

  const fetchTasks = async () => {
    try {
      let url = `${API_URL}/api/v1/tasks`;
      if (selectedStatus !== 'all') {
        url += `?status=${selectedStatus}`;
      }

      const response = await fetch(url, { credentials: 'include' });
      const data = await response.json();
      setTasks(limit ? data.slice(0, limit) : data);
    } catch (error) {
      console.error('Error fetching tasks:', error);
    } finally {
      setLoading(false);
    }
  };

  const updateTaskStatus = async (taskId: string, newStatus: string) => {
    try {
      await fetch(`${API_URL}/api/v1/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status: newStatus }),
      });
      fetchTasks();
    } catch (error) {
      console.error('Error updating task:', error);
    }
  };

  const syncToGithub = async (taskId: string) => {
    if (!isAuthenticated) {
      alert('Please sign in with GitHub first');
      return;
    }
    if (!user?.default_github_repo) {
      alert('Please select a default repository first');
      return;
    }

    setSyncingTasks(prev => new Set(prev).add(taskId));

    try {
      const response = await fetch(`${API_URL}/api/v1/tasks/${taskId}/sync-to-github`, {
        method: 'POST',
        credentials: 'include',
      });

      if (response.ok) {
        const result = await response.json();
        // Refresh the tasks to get updated sync status
        fetchTasks();
        console.log('Synced to GitHub:', result);
      } else {
        const error = await response.json();
        alert(`Sync failed: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Error syncing to GitHub:', error);
      alert('Failed to sync to GitHub');
    } finally {
      setSyncingTasks(prev => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'No deadline';
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.ceil((date.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays < 0) return <span className="text-red-400">Overdue by {Math.abs(diffDays)}d</span>;
    if (diffDays === 0) return <span className="text-yellow-400">Due today</span>;
    if (diffDays <= 3) return <span className="text-orange-400">Due in {diffDays}d</span>;
    return <span className="text-slate-400">{date.toLocaleDateString()}</span>;
  };

  const getSyncStatusBadge = (task: Task) => {
    const syncStatus = task.github_sync_status || 'not_synced';
    const isSyncing = syncingTasks.has(task.id);

    if (isSyncing) {
      return (
        <span className="flex items-center gap-1 text-xs bg-yellow-600 text-yellow-100 px-2 py-0.5 rounded-full">
          <span className="animate-spin">↻</span>
          Syncing...
        </span>
      );
    }

    if (task.github_issue_number) {
      return (
        <a
          href={task.github_issue_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs bg-green-600/80 hover:bg-green-600 text-green-100 px-2 py-0.5 rounded-full transition-colors"
          title={`Issue #${task.github_issue_number} on ${task.github_repo}`}
        >
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
          </svg>
          #{task.github_issue_number}
        </a>
      );
    }

    const statusInfo = syncStatusColors[syncStatus] || syncStatusColors.not_synced;
    return (
      <span className={`flex items-center gap-1 text-xs ${statusInfo.bg} ${statusInfo.text} px-2 py-0.5 rounded-full`}>
        {statusInfo.icon}
      </span>
    );
  };

  if (loading) {
    return <div className="text-center py-8 text-slate-400">Loading tasks...</div>;
  }

  return (
    <div>
      {!limit && (
        <div className="flex gap-2 mb-4">
          {['all', 'not_started', 'in_progress', 'blocked', 'completed'].map((status) => (
            <button
              key={status}
              onClick={() => setSelectedStatus(status)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${selectedStatus === status
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
            >
              {status.replace('_', ' ')}
            </button>
          ))}
        </div>
      )}

      <div className="space-y-3">
        {tasks.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            No tasks found. Create your first task to get started!
          </div>
        ) : (
          tasks.map((task) => (
            <div
              key={task.id}
              className="bg-slate-700/30 border border-slate-600/50 rounded-xl p-4 hover:bg-slate-700/50 transition-all group"
            >
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-white">{task.name}</h3>
                    <span className={`text-xs font-bold ${priorityColors[task.priority] || 'text-slate-400'}`}>
                      {task.priority.toUpperCase()}
                    </span>
                    {/* Sync Status Badge */}
                    {getSyncStatusBadge(task)}
                  </div>
                  <p className="text-sm text-slate-400">Assigned to: {task.owner}</p>
                </div>

                <div className="text-right">
                  <div className="text-xs mb-2">{formatDate(task.deadline)}</div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[task.status] || 'bg-slate-600 text-slate-200'}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="flex gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                {task.status !== 'completed' && (
                  <>
                    {task.status !== 'in_progress' && (
                      <button
                        onClick={() => updateTaskStatus(task.id, 'in_progress')}
                        className="text-xs px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded transition-colors"
                      >
                        Start
                      </button>
                    )}
                    {task.status === 'in_progress' && (
                      <button
                        onClick={() => updateTaskStatus(task.id, 'completed')}
                        className="text-xs px-3 py-1 bg-green-600 hover:bg-green-700 rounded transition-colors"
                      >
                        Complete
                      </button>
                    )}
                    <button
                      onClick={() => updateTaskStatus(task.id, 'blocked')}
                      className="text-xs px-3 py-1 bg-red-600 hover:bg-red-700 rounded transition-colors"
                    >
                      Block
                    </button>
                  </>
                )}

                {/* GitHub Sync Button */}
                {isAuthenticated && !task.github_issue_number && !syncingTasks.has(task.id) && (
                  <button
                    onClick={() => syncToGithub(task.id)}
                    className="text-xs px-3 py-1 bg-slate-600 hover:bg-slate-500 rounded transition-colors flex items-center gap-1 ml-auto"
                    title="Sync to GitHub Issues"
                  >
                    <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                    </svg>
                    Sync to GitHub
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}