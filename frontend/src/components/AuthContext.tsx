'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Types
interface User {
    id: string;
    email: string;
    name: string;
    role: string;
    github_username?: string;
    github_avatar_url?: string;
    default_github_repo?: string;
    is_github_connected: boolean;
}

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: () => void;
    logout: () => Promise<void>;
    refreshUser: () => Promise<void>;
    setDefaultRepo: (repo: string) => Promise<void>;
}

// Create context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// API base URL
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Provider component
export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Check auth status on mount
    useEffect(() => {
        checkAuthStatus();

        // Check for auth_success in URL (after OAuth callback)
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('auth_success') === 'true') {
            // Remove the query param and refresh user
            window.history.replaceState({}, '', window.location.pathname);
            checkAuthStatus();
        }
    }, []);

    const checkAuthStatus = async () => {
        try {
            const response = await fetch(`${API_URL}/auth/status`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (response.ok) {
                const data = await response.json();
                if (data.authenticated && data.user) {
                    setUser(data.user);
                } else {
                    setUser(null);
                }
            } else {
                setUser(null);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    };

    const login = () => {
        // Redirect to GitHub OAuth
        const currentPath = window.location.pathname;
        window.location.href = `${API_URL}/auth/github?redirect_to=${encodeURIComponent(currentPath)}`;
    };

    const logout = async () => {
        try {
            await fetch(`${API_URL}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
            });
        } catch (error) {
            console.error('Logout failed:', error);
        }
        setUser(null);
    };

    const refreshUser = async () => {
        await checkAuthStatus();
    };

    const setDefaultRepo = async (repo: string) => {
        try {
            const response = await fetch(`${API_URL}/auth/set-default-repo`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ repo }),
            });

            if (response.ok) {
                await refreshUser();
            } else {
                throw new Error('Failed to set default repo');
            }
        } catch (error) {
            console.error('Set default repo failed:', error);
            throw error;
        }
    };

    const value: AuthContextType = {
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        logout,
        refreshUser,
        setDefaultRepo,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

// Hook to use auth context
export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

// Export the context for advanced usage
export { AuthContext };
