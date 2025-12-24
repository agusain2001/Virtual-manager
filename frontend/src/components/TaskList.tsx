'use client';

import { useEffect, useState } from 'react';

type Task = {
  id: string;
  name: string;
  project_id: string;
  owner: string;
  priority: string;
  status: string;
  deadline: string | null;
  created_at: string;
};

const statusColors = {
  not_started: 'bg-slate-600 text-slate-200',
  in_progress: 'bg-blue-600 text-blue-100',
  blocked: 'bg-red-600 text-red-100',
  completed: 'bg-green-600 text-green-100',
  cancelled: 'bg-gray-600 text-gray-200',
};

const priorityColors = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-yellow-400',
  low: 'text-green-400',
};

export default function TaskList({ limit, refreshKey }: { limit?: number; refreshKey?: number }) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedStatus, setSelectedStatus] = useState<string>('all');

  useEffect(() => {
    fetchTasks();
  }, [refreshKey, selectedStatus]);

  const fetchTasks = async () => {
    try {
      let url = 'http://localhost:8000/api/v1/tasks';
      if (selectedStatus !== 'all') {
        url += `?status=${selectedStatus}`;
      }
      
      const response = await fetch(url);
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
      await fetch(`http://localhost:8000/api/v1/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      fetchTasks();
    } catch (error) {
      console.error('Error updating task:', error);
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
              className={`px-3 py-1 rounded-lg text-sm font-medium transition-all ${
                selectedStatus === status
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
                    <span className={`text-xs font-bold ${priorityColors[task.priority as keyof typeof priorityColors]}`}>
                      {task.priority.toUpperCase()}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400">Assigned to: {task.owner}</p>
                </div>
                
                <div className="text-right">
                  <div className="text-xs mb-2">{formatDate(task.deadline)}</div>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColors[task.status as keyof typeof statusColors]}`}>
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
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}