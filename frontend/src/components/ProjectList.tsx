'use client';

import { useEffect, useState } from 'react';

type Project = {
  id: string;
  name: string;
  owner: string;
  objective: string;
  priority: string;
  health: string;
  created_at: string;
};

const healthColors = {
  on_track: 'bg-green-500/20 text-green-400 border-green-500/30',
  at_risk: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  delayed: 'bg-red-500/20 text-red-400 border-red-500/30',
};

export function ProjectList({ limit, refreshKey }: { limit?: number; refreshKey?: number }) {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/v1/projects')
      .then(res => res.json())
      .then(data => setProjects(limit ? data.slice(0, limit) : data))
      .catch(console.error);
  }, [refreshKey, limit]);

  return (
    <div className="space-y-3">
      {projects.length === 0 ? (
        <div className="text-center py-8 text-slate-500">
          No projects yet. Create your first project!
        </div>
      ) : (
        projects.map((project) => (
          <div
            key={project.id}
            className="bg-slate-700/30 border border-slate-600/50 rounded-xl p-4 hover:bg-slate-700/50 transition-all"
          >
            <div className="flex justify-between items-start mb-2">
              <div>
                <h3 className="font-semibold text-white">{project.name}</h3>
                <p className="text-sm text-slate-400 mt-1">Owner: {project.owner}</p>
                {project.objective && (
                  <p className="text-xs text-slate-500 mt-2 line-clamp-2">{project.objective}</p>
                )}
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium border ${healthColors[project.health as keyof typeof healthColors]}`}>
                {project.health.replace('_', ' ')}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}