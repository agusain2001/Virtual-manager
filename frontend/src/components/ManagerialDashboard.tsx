"use client";

import React, { useState } from 'react';
import { 
  Shield, TrendingUp, Target, MessageSquare, 
  FileText, Bell, Users, HelpCircle 
} from 'lucide-react';

const API_BASE_URL = "http://localhost:8000"; // Adjust port if needed

export default function ManagerialDashboard() {
  const [activeTab, setActiveTab] = useState<'strategy' | 'communication' | 'intelligence'>('strategy');
  const [subTab, setSubTab] = useState<string>('risks'); // For sub-navigation
  const [isLoading, setIsLoading] = useState(false);
  
  // --- STATE ---
  // Strategy
  const [goalInput, setGoalInput] = useState("");
  const [structuredGoal, setStructuredGoal] = useState<any>(null);
  const [riskAnalysis, setRiskAnalysis] = useState<any>(null);
  
  // Communication
  const [reportResult, setReportResult] = useState<any>(null);
  const [standupResult, setStandupResult] = useState<any>(null);
  const [reminderResult, setReminderResult] = useState<any>(null);
  
  // Intelligence
  const [transcript, setTranscript] = useState("");
  const [meetingSummary, setMeetingSummary] = useState<any>(null);
  const [stakeholderQuery, setStakeholderQuery] = useState("");
  const [queryResponse, setQueryResponse] = useState<any>(null);

  // --- API HELPERS ---
  const post = async (endpoint: string, body: any) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/managerial/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      return await res.json();
    } catch (e) {
      console.error(e);
      alert("API Error");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden font-sans">
      {/* Header */}
      <div className="bg-slate-900 text-white p-5 flex items-center gap-3">
        <Shield className="w-8 h-8 text-blue-400" />
        <div>
          <h2 className="text-xl font-bold">Virtual Manager AI</h2>
          <p className="text-slate-400 text-xs uppercase tracking-wide">Managerial Intelligence Layer</p>
        </div>
      </div>

      {/* Main Tabs */}
      <div className="flex bg-gray-50 border-b border-gray-200">
        {[
          { id: 'strategy', label: 'Strategy & Risk', icon: TrendingUp },
          { id: 'communication', label: 'Communication', icon: MessageSquare },
          { id: 'intelligence', label: 'Intelligence', icon: Users },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => { setActiveTab(tab.id as any); setSubTab(tab.id === 'strategy' ? 'risks' : tab.id === 'communication' ? 'standup' : 'meetings'); }}
            className={`flex-1 py-4 flex items-center justify-center gap-2 text-sm font-semibold transition-colors ${
              activeTab === tab.id ? 'bg-white text-blue-600 border-t-2 border-blue-600' : 'text-gray-500 hover:bg-gray-100'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-6 min-h-[500px]">
        
        {/* ================= STRATEGY TAB ================= */}
        {activeTab === 'strategy' && (
          <div className="space-y-6">
            <div className="flex gap-2 mb-4">
              <button onClick={() => setSubTab('risks')} className={`px-3 py-1 rounded-full text-sm ${subTab === 'risks' ? 'bg-blue-100 text-blue-700 font-bold' : 'bg-gray-100'}`}>Risk Analysis</button>
              <button onClick={() => setSubTab('goals')} className={`px-3 py-1 rounded-full text-sm ${subTab === 'goals' ? 'bg-blue-100 text-blue-700 font-bold' : 'bg-gray-100'}`}>Goal Planning</button>
            </div>

            {subTab === 'risks' && (
              <div>
                <button 
                  onClick={async () => {
                    const res = await post('analyze-risks', { tasks: [{ title: "DB Migration", status: "Delayed" }], goals: [{ title: "Uptime" }] });
                    setRiskAnalysis(res);
                  }}
                  className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 mb-4"
                >
                  {isLoading ? "Analyzing..." : "Analyze Current Project Risks"}
                </button>
                {riskAnalysis && (
                  <div className="space-y-4">
                    <div className="p-4 bg-red-50 text-red-800 rounded border border-red-100">{riskAnalysis.overall_assessment}</div>
                    {riskAnalysis.risks.map((r: any, i: number) => (
                      <div key={i} className="border p-4 rounded shadow-sm">
                        <div className="font-bold flex justify-between">
                          {r.description} 
                          <span className="text-xs bg-gray-200 px-2 py-1 rounded">{r.likelihood} Likelihood</span>
                        </div>
                        <div className="text-sm mt-2 text-gray-600">Mitigation: {r.mitigations[0]?.strategy}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {subTab === 'goals' && (
              <div className="max-w-xl">
                <label className="block text-sm font-medium text-gray-700 mb-2">Refine Organizational Goal</label>
                <div className="flex gap-2">
                  <input 
                    className="flex-1 border p-2 rounded" 
                    placeholder="e.g. Increase user retention" 
                    value={goalInput}
                    onChange={(e) => setGoalInput(e.target.value)}
                  />
                  <button 
                    onClick={async () => {
                      const res = await post('refine-goal', { raw_text: goalInput });
                      setStructuredGoal(res);
                    }}
                    className="bg-blue-600 text-white px-4 py-2 rounded"
                  >
                    Refine
                  </button>
                </div>
                {structuredGoal && (
                  <div className="mt-4 bg-slate-50 p-4 rounded border border-slate-200">
                    <h4 className="font-bold text-slate-800">Structured Goal Output</h4>
                    <div className="mt-2 grid grid-cols-2 gap-4 text-sm">
                      <div><span className="font-semibold">Objective:</span> {structuredGoal.objective}</div>
                      <div><span className="font-semibold">Owner:</span> {structuredGoal.owner || "Unassigned"}</div>
                      <div className="col-span-2"><span className="font-semibold">KPIs:</span> {structuredGoal.kpis.join(", ")}</div>
                      <div className="col-span-2">
                        <span className="font-semibold">Status:</span> 
                        {structuredGoal.is_measurable ? 
                          <span className="text-green-600 font-bold ml-2">Measurable</span> : 
                          <span className="text-red-600 font-bold ml-2">Vague ({structuredGoal.missing_criteria})</span>
                        }
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================= COMMUNICATION TAB ================= */}
        {activeTab === 'communication' && (
          <div className="space-y-6">
            <div className="flex gap-2 mb-4">
              <button onClick={() => setSubTab('standup')} className={`px-3 py-1 rounded-full text-sm ${subTab === 'standup' ? 'bg-purple-100 text-purple-700 font-bold' : 'bg-gray-100'}`}>Standup</button>
              <button onClick={() => setSubTab('reports')} className={`px-3 py-1 rounded-full text-sm ${subTab === 'reports' ? 'bg-purple-100 text-purple-700 font-bold' : 'bg-gray-100'}`}>Reports</button>
              <button onClick={() => setSubTab('reminders')} className={`px-3 py-1 rounded-full text-sm ${subTab === 'reminders' ? 'bg-purple-100 text-purple-700 font-bold' : 'bg-gray-100'}`}>Reminders</button>
            </div>

            {subTab === 'standup' && (
              <div>
                <button 
                  onClick={async () => {
                    const res = await post('generate-standup', { 
                      completed_work: ["Built API", "Fixed Login"], 
                      planned_work: ["Testing"], 
                      blockers: ["None"] 
                    });
                    setStandupResult(res);
                  }}
                  className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
                >
                  Generate Daily Standup
                </button>
                {standupResult && (
                  <div className="mt-4 p-4 bg-purple-50 rounded border border-purple-100 text-sm">
                    <p className="mb-2 font-medium">{standupResult.summary}</p>
                    <ul className="list-disc ml-5 text-gray-600">{standupResult.action_items.map((i:any, k:number) => <li key={k}>{i}</li>)}</ul>
                  </div>
                )}
              </div>
            )}

            {subTab === 'reports' && (
              <div>
                 <button 
                  onClick={async () => {
                    const res = await post('generate-report', { 
                      report_type: "Weekly", 
                      audience: "Executive",
                      goals_progress: ["On Track"], key_achievements: ["Launched V1"], risks_mitigations: ["None"], upcoming_priorities: ["Scale"]
                    });
                    setReportResult(res);
                  }}
                  className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
                >
                  Generate Weekly Executive Report
                </button>
                {reportResult && (
                   <div className="mt-4 p-4 bg-indigo-50 rounded border border-indigo-100 text-sm whitespace-pre-wrap">
                     {reportResult.report_content}
                   </div>
                )}
              </div>
            )}

             {subTab === 'reminders' && (
              <div className="max-w-md">
                <button 
                  onClick={async () => {
                    const res = await post('generate-reminder', { 
                      recipient: "Dev Team", topic: "Code Freeze", context: "Release is tomorrow", tone: "Respectful"
                    });
                    setReminderResult(res);
                  }}
                  className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700"
                >
                  Draft Reminder Message
                </button>
                {reminderResult && (
                   <div className="mt-4 p-4 bg-orange-50 rounded border border-orange-100 text-sm italic">
                     "{reminderResult.message}"
                   </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================= INTELLIGENCE TAB ================= */}
        {activeTab === 'intelligence' && (
          <div className="space-y-6">
             <div className="flex gap-2 mb-4">
              <button onClick={() => setSubTab('meetings')} className={`px-3 py-1 rounded-full text-sm ${subTab === 'meetings' ? 'bg-green-100 text-green-700 font-bold' : 'bg-gray-100'}`}>Meeting Summarizer</button>
              <button onClick={() => setSubTab('ask')} className={`px-3 py-1 rounded-full text-sm ${subTab === 'ask' ? 'bg-green-100 text-green-700 font-bold' : 'bg-gray-100'}`}>Ask Manager</button>
            </div>

            {subTab === 'meetings' && (
              <div>
                <textarea 
                  className="w-full border p-2 rounded mb-2 text-sm" 
                  rows={4} 
                  placeholder="Paste meeting transcript here..."
                  value={transcript}
                  onChange={(e) => setTranscript(e.target.value)}
                />
                <button 
                  onClick={async () => {
                    const res = await post('summarize-conversation', { transcript });
                    setMeetingSummary(res);
                  }}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >
                  Summarize Decisions & Actions
                </button>
                {meetingSummary && (
                  <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
                    <div className="bg-green-50 p-3 rounded">
                      <h5 className="font-bold text-green-800">Decisions</h5>
                      <ul className="list-disc ml-4">{meetingSummary.decisions.map((d:any, i:number) => <li key={i}>{d}</li>)}</ul>
                    </div>
                     <div className="bg-blue-50 p-3 rounded">
                      <h5 className="font-bold text-blue-800">Action Items</h5>
                      <ul className="list-disc ml-4">{meetingSummary.action_items.map((d:any, i:number) => <li key={i}>{d}</li>)}</ul>
                    </div>
                  </div>
                )}
              </div>
            )}

            {subTab === 'ask' && (
              <div>
                <div className="flex gap-2 mb-4">
                  <input 
                    className="flex-1 border p-2 rounded" 
                    placeholder="Ask a question about the project..." 
                    value={stakeholderQuery}
                    onChange={(e) => setStakeholderQuery(e.target.value)}
                  />
                  <button 
                    onClick={async () => {
                      const res = await post('ask-stakeholder', { query: stakeholderQuery, project_context: "Project is currently delayed by 2 days due to DB issues." });
                      setQueryResponse(res);
                    }}
                    className="bg-teal-600 text-white px-4 py-2 rounded"
                  >
                    Ask
                  </button>
                </div>
                {queryResponse && (
                  <div className="bg-teal-50 p-4 rounded border border-teal-100">
                    <p className="text-gray-800 mb-2">{queryResponse.answer}</p>
                    <p className="text-xs text-gray-500 font-semibold uppercase">Reasoning: {queryResponse.reasoning}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}