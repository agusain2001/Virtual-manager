'use client';

import React, { useState, useEffect } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApprovalBadgeProps {
    onClick?: () => void;
    className?: string;
}

/**
 * Notification badge that shows the count of pending approvals.
 * Polls the API every 30 seconds to stay updated.
 * 
 * Phase 4: Safety & Governance
 */
export default function ApprovalBadge({ onClick, className = '' }: ApprovalBadgeProps) {
    const [count, setCount] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchCount();
        // Poll every 30 seconds
        const interval = setInterval(fetchCount, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchCount = async () => {
        try {
            const res = await fetch(`${API_URL}/managerial/approvals/count`, {
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setCount(data.pending_count || 0);
            }
        } catch (err) {
            console.error('Failed to fetch approval count:', err);
        } finally {
            setLoading(false);
        }
    };

    if (loading || count === 0) {
        return null;
    }

    return (
        <button
            onClick={onClick}
            className={`relative inline-flex items-center justify-center p-2 rounded-lg 
                bg-red-500/20 hover:bg-red-500/30 border border-red-500/50 
                text-red-400 hover:text-red-300 transition-all
                ${className}`}
            title={`${count} pending approval${count !== 1 ? 's' : ''}`}
        >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>

            {/* Badge count */}
            <span className="absolute -top-1 -right-1 flex items-center justify-center 
                min-w-[18px] h-[18px] px-1 text-xs font-bold 
                bg-red-500 text-white rounded-full
                animate-pulse">
                {count > 99 ? '99+' : count}
            </span>
        </button>
    );
}

/**
 * Inline text badge showing pending approval count.
 * Alternative simpler version for use in headers/navs.
 */
export function ApprovalCountBadge({ className = '' }: { className?: string }) {
    const [count, setCount] = useState(0);

    useEffect(() => {
        fetchCount();
        const interval = setInterval(fetchCount, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchCount = async () => {
        try {
            const res = await fetch(`${API_URL}/managerial/approvals/count`, {
                credentials: 'include'
            });
            if (res.ok) {
                const data = await res.json();
                setCount(data.pending_count || 0);
            }
        } catch {
            // Silent fail
        }
    };

    if (count === 0) return null;

    return (
        <span className={`inline-flex items-center gap-1.5 px-2 py-1 
            text-xs font-medium rounded-full
            bg-red-500/20 text-red-400 border border-red-500/30
            ${className}`}
        >
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
            {count} pending
        </span>
    );
}
