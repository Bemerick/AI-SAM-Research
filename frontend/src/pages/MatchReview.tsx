import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { matchesAPI } from '../services/api';
import MatchCard from '../components/MatchCard';
import type { MatchStatus } from '../types';
import { MATCH_STATUSES } from '../types';

export default function MatchReview() {
  const [statusFilter, setStatusFilter] = useState<MatchStatus>('pending_review');
  const queryClient = useQueryClient();

  const { data: matches, isLoading, error } = useQuery({
    queryKey: ['matches', statusFilter],
    queryFn: () => matchesAPI.list({ status: statusFilter }),
  });

  const updateMatchMutation = useMutation({
    mutationFn: ({ matchId, status }: { matchId: number; status: string }) =>
      matchesAPI.update(matchId, { status: status as MatchStatus, reviewed_by: 'current.user@company.com' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] });
    },
  });

  const handleStatusChange = (matchId: number, status: string) => {
    updateMatchMutation.mutate({ matchId, status });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card max-w-md mx-auto mt-12">
        <div className="text-red-600 mb-2">⚠️ Error Loading Matches</div>
        <p className="text-gray-600">{error instanceof Error ? error.message : 'Failed to load'}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Match Review</h1>
        <p className="text-gray-600 mt-1">Review GovWin matches for SAM.gov opportunities</p>
      </div>

      {/* Status Filter */}
      <div className="card mb-6">
        <label className="label">Filter by Status</label>
        <div className="flex gap-2 flex-wrap">
          {MATCH_STATUSES.map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`btn btn-sm ${
                statusFilter === status ? 'btn-primary' : 'btn-secondary'
              }`}
            >
              {status.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {matches && matches.length === 0 && (
        <div className="card text-center py-12">
          <div className="text-6xl mb-4">✅</div>
          <h3 className="text-xl font-semibold text-gray-900 mb-2">No Matches Found</h3>
          <p className="text-gray-600">
            No matches with status "{statusFilter.replace('_', ' ')}" found.
          </p>
        </div>
      )}

      {/* Matches Grid */}
      {matches && matches.length > 0 && (
        <div>
          <div className="mb-4 text-sm text-gray-600">
            Showing {matches.length} match{matches.length !== 1 ? 'es' : ''}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {matches.map((match) => (
              <MatchCard
                key={match.id}
                match={match}
                onStatusChange={handleStatusChange}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
