'use client';

import { useEffect, useState, useRef } from 'react';

type Activity = {
  id: string;
  timestamp: string;
  agent_name: string;
  activity_type: string;
  message: string;
};

export function AgentActivityLog() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchActivities();
    const interval = setInterval(fetchActivities, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchActivities = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/activities?limit=30');
      const data = await response.json();
      setActivities(data);
    } catch (error) {
      console.error('Error fetching activities:', error);
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activities]);

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getAgentColor = (agent: string) => {
    const colors: Record<string, string> = {
      'Orchestrator': 'text-purple-400',
      'Planning': 'text-blue-400',
      'Execution': 'text-green-400',
      'Communication': 'text-yellow-400',
      'PeopleOps': 'text-pink-400',
      'TaskManager': 'text-cyan-400',
    };
    return colors[agent] || 'text-slate-400';
  };

  return (
    <div className="h-[400px] overflow-y-auto p-6 space-y-3 font-mono text-sm" ref={scrollRef}>
      {activities.length === 0 ? (
        <div className="text-center text-slate-600 mt-20">Waiting for system signals...</div>
      ) : (
        activities.map((activity) => (
          <div key={activity.id} className="flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <span className="text-slate-500 whitespace-nowrap">{formatTime(activity.timestamp)}</span>
            <div className="flex-1">
              <span className={`font-bold mr-2 ${getAgentColor(activity.agent_name)}`}>
                [{activity.agent_name}]
              </span>
              <span className={activity.activity_type === 'decision' ? 'text-amber-300' : 'text-slate-300'}>
                {activity.activity_type === 'decision' ? '➔ ' : ''}{activity.message}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}