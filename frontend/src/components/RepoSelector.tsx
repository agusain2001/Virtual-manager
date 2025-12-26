'use client';

import { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';

interface Repo {
    id: number;
    full_name: string;
    name: string;
    private: boolean;
    description: string | null;
    html_url: string;
}

export default function RepoSelector() {
    const { user, setDefaultRepo, refreshUser } = useAuth();
    const [repos, setRepos] = useState<Repo[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    const fetchRepos = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await fetch(`${API_URL}/auth/repos`, {
                credentials: 'include',
            });
            if (response.ok) {
                const data = await response.json();
                setRepos(data);
            } else {
                throw new Error('Failed to fetch repos');
            }
        } catch (err) {
            setError('Failed to load repositories');
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSelectRepo = async (repo: string) => {
        try {
            await setDefaultRepo(repo);
            setIsOpen(false);
        } catch (err) {
            setError('Failed to set repository');
        }
    };

    useEffect(() => {
        if (isOpen && repos.length === 0) {
            fetchRepos();
        }
    }, [isOpen]);

    if (!user?.is_github_connected) {
        return null;
    }

    return (
        <div className="relative">
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-600 rounded-lg text-sm transition-colors"
            >
                <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span className="text-slate-300">
                    {user.default_github_repo || 'Select Repository'}
                </span>
                <svg className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {isOpen && (
                <div className="absolute top-full mt-2 w-80 bg-slate-800 border border-slate-600 rounded-lg shadow-xl z-50 max-h-96 overflow-auto">
                    <div className="p-2 border-b border-slate-600">
                        <p className="text-xs text-slate-400 px-2">Select a repository for GitHub sync</p>
                    </div>

                    {isLoading && (
                        <div className="p-4 text-center text-slate-400">
                            <div className="animate-spin h-5 w-5 border-2 border-slate-400 border-t-transparent rounded-full mx-auto mb-2"></div>
                            Loading repositories...
                        </div>
                    )}

                    {error && (
                        <div className="p-4 text-center text-red-400 text-sm">
                            {error}
                            <button onClick={fetchRepos} className="block mx-auto mt-2 text-blue-400 hover:underline">
                                Try again
                            </button>
                        </div>
                    )}

                    {!isLoading && !error && repos.length === 0 && (
                        <div className="p-4 text-center text-slate-400 text-sm">
                            No repositories found
                        </div>
                    )}

                    {!isLoading && repos.map((repo) => (
                        <button
                            key={repo.id}
                            onClick={() => handleSelectRepo(repo.full_name)}
                            className={`w-full px-4 py-3 text-left hover:bg-slate-700 transition-colors border-b border-slate-700 last:border-b-0 ${user.default_github_repo === repo.full_name ? 'bg-slate-700' : ''
                                }`}
                        >
                            <div className="flex items-center gap-2">
                                <svg className="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                                </svg>
                                <span className="text-white font-medium">{repo.name}</span>
                                {repo.private && (
                                    <span className="text-xs bg-slate-600 text-slate-300 px-1.5 py-0.5 rounded">Private</span>
                                )}
                                {user.default_github_repo === repo.full_name && (
                                    <svg className="w-4 h-4 text-green-400 ml-auto" fill="currentColor" viewBox="0 0 20 20">
                                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                )}
                            </div>
                            {repo.description && (
                                <p className="text-xs text-slate-400 mt-1 truncate pl-6">{repo.description}</p>
                            )}
                            <p className="text-xs text-slate-500 mt-0.5 pl-6">{repo.full_name}</p>
                        </button>
                    ))}
                </div>
            )}

            {/* Backdrop */}
            {isOpen && (
                <div
                    className="fixed inset-0 z-40"
                    onClick={() => setIsOpen(false)}
                />
            )}
        </div>
    );
}
