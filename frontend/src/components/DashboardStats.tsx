'use client';

import { useEffect, useState } from 'react';

type Stats = {
  total_projects: number;
  total_tasks: number;
  pending_tasks: number;
  blocked_tasks: number;
  completed_tasks: number;
  overdue_tasks: number;
  completion_rate: number;
};

export default function DashboardStats({ refreshKey }: { refreshKey?: number }) {
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/dashboard/stats')
      .then(res => res.json())
      .then(setStats)
      .catch(console.error);
  }, [refreshKey]);

  if (!stats) return <div className="text-slate-400">Loading stats...</div>;

  const statCards = [
    { label: 'Total Projects', value: stats.total_projects, color: 'from-purple-500 to-purple-600', icon: '📁' },
    { label: 'Total Tasks', value: stats.total_tasks, color: 'from-blue-500 to-blue-600', icon: '📋' },
    { label: 'Pending', value: stats.pending_tasks, color: 'from-yellow-500 to-yellow-600', icon: '⏳' },
    { label: 'Blocked', value: stats.blocked_tasks, color: 'from-red-500 to-red-600', icon: '🚫' },
    { label: 'Completed', value: stats.completed_tasks, color: 'from-green-500 to-green-600', icon: '✅' },
    { label: 'Overdue', value: stats.overdue_tasks, color: 'from-orange-500 to-orange-600', icon: '⚠️' },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      {statCards.map((stat, index) => (
        <div
          key={index}
          className="bg-slate-800/50 backdrop-blur-xl border border-slate-700/50 rounded-xl p-4 shadow-lg hover:scale-105 transition-transform"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-2xl">{stat.icon}</span>
            <div className={`text-2xl font-bold bg-gradient-to-r ${stat.color} bg-clip-text text-transparent`}>
              {stat.value}
            </div>
          </div>
          <div className="text-sm text-slate-400">{stat.label}</div>
        </div>
      ))}
    </div>
  );
}