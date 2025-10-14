import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { samOpportunitiesAPI, matchesAPI, crmAPI } from '../services/api';
import FitScoreBadge from '../components/FitScoreBadge';
import WorkflowControls from '../components/WorkflowControls';
import MatchCard from '../components/MatchCard';
import ContractCard from '../components/ContractCard';
import { formatDate, daysUntilDeadline, getUrgencyClass } from '../utils/formatters';
import { useState } from 'react';
import type { MatchWithDetails, MatchStatus } from '../types';

// Component to display a match with its contracts
function MatchWithContracts({
  match,
  opportunityId,
  onStatusChange,
  onDelete
}: {
  match: MatchWithDetails;
  opportunityId: number;
  onStatusChange?: (matchId: number, status: string) => void;
  onDelete?: (matchId: number) => void;
}) {
  const { data: contracts, isLoading } = useQuery({
    queryKey: ['match-contracts', opportunityId, match.id],
    queryFn: () => samOpportunitiesAPI.getMatchContracts(opportunityId, match.id),
    enabled: opportunityId > 0 && match.id > 0,
  });

  return (
    <div>
      <div className="flex gap-2 mb-2">
        <div className="flex-1">
          <MatchCard match={match} onStatusChange={onStatusChange} />
        </div>
        {onDelete && (
          <button
            onClick={() => onDelete(match.id)}
            className="btn btn-danger self-start"
            title="Remove this match"
          >
            Remove Match
          </button>
        )}
      </div>

      {/* Contracts for this match */}
      {contracts && contracts.length > 0 && (
        <div className="mt-4 ml-4">
          <h4 className="text-lg font-semibold text-gray-900 mb-3">
            Related Contracts ({contracts.length})
          </h4>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {contracts.map((contract) => (
              <ContractCard key={contract.id} contract={contract} />
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="mt-4 ml-4 text-gray-500 text-sm">
          Loading contracts...
        </div>
      )}
    </div>
  );
}

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>();
  const opportunityId = parseInt(id || '0');
  const queryClient = useQueryClient();

  const [localOpportunity, setLocalOpportunity] = useState<any>(null);

  const { data: opportunity, isLoading, error } = useQuery({
    queryKey: ['sam-opportunity', opportunityId],
    queryFn: () => samOpportunitiesAPI.getById(opportunityId),
    enabled: opportunityId > 0,
  });

  const { data: matches } = useQuery({
    queryKey: ['opportunity-matches', opportunityId],
    queryFn: () => samOpportunitiesAPI.getMatches(opportunityId),
    enabled: opportunityId > 0,
  });

  // Mutation for updating match status
  const updateMatchMutation = useMutation({
    mutationFn: ({ matchId, status }: { matchId: number; status: string }) =>
      matchesAPI.update(matchId, { status: status as MatchStatus, reviewed_by: 'current.user@company.com' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunity-matches', opportunityId] });
    },
  });

  // Mutation for deleting a match
  const deleteMatchMutation = useMutation({
    mutationFn: (matchId: number) => matchesAPI.delete(matchId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['opportunity-matches', opportunityId] });
    },
  });

  const handleStatusChange = (matchId: number, status: string) => {
    updateMatchMutation.mutate({ matchId, status });
  };

  const handleDeleteMatch = (matchId: number) => {
    if (confirm('Are you sure you want to remove this match?')) {
      deleteMatchMutation.mutate(matchId);
    }
  };

  // Mutation for sending to CRM
  const sendToCRMMutation = useMutation({
    mutationFn: (opportunityId: number) => crmAPI.sendToCRM(opportunityId),
    onSuccess: (data) => {
      alert(`Success! Opportunity sent to CRM.\n\nCRM ID: ${data.crm_result?.crm_id || 'N/A'}\n${data.crm_result?.message || ''}`);
    },
    onError: (error: any) => {
      alert(`Failed to send to CRM: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleSendToCRM = () => {
    if (confirm('Send this opportunity to Microsoft Dynamics CRM?')) {
      sendToCRMMutation.mutate(opportunityId);
    }
  };

  const currentOpp = localOpportunity || opportunity;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  if (error || !currentOpp) {
    return (
      <div className="card max-w-2xl mx-auto mt-12">
        <div className="text-red-600 mb-2">⚠️ Opportunity Not Found</div>
        <p className="text-gray-600 mb-4">The requested opportunity could not be loaded.</p>
        <Link to="/" className="btn btn-primary">
          Back to Opportunities
        </Link>
      </div>
    );
  }

  const days = daysUntilDeadline(currentOpp.response_deadline);
  const urgencyClass = getUrgencyClass(currentOpp.response_deadline);

  return (
    <div>
      {/* Back Button */}
      <Link to="/" className="text-primary-600 hover:text-primary-700 mb-4 inline-block">
        ← Back to Opportunities
      </Link>

      {/* Header */}
      <div className="card mb-6">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{currentOpp.title}</h1>
            <p className="text-gray-600">Notice ID: {currentOpp.notice_id}</p>
          </div>
          <div className="flex items-center gap-3">
            <FitScoreBadge score={currentOpp.fit_score} showLabel={true} />
            <button
              onClick={handleSendToCRM}
              disabled={sendToCRMMutation.isPending}
              className="btn btn-primary"
              title="Send this opportunity to Microsoft Dynamics CRM"
            >
              {sendToCRMMutation.isPending ? (
                <>
                  <span className="inline-block animate-spin mr-2">⏳</span>
                  Sending...
                </>
              ) : (
                <>
                  📤 Send to CRM
                </>
              )}
            </button>
          </div>
        </div>

        {/* Key Information Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-sm font-medium text-gray-500">Department</label>
            <p className="text-gray-900">{currentOpp.department || 'N/A'}</p>
          </div>

          {currentOpp.solicitation_number && (
            <div>
              <label className="text-sm font-medium text-gray-500">Solicitation Number</label>
              <p className="text-gray-900">{currentOpp.solicitation_number}</p>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-gray-500">NAICS Code</label>
            <p className="text-gray-900">{currentOpp.naics_code || 'N/A'}</p>
          </div>

          {currentOpp.assigned_practice_area && (
            <div>
              <label className="text-sm font-medium text-gray-500">Practice Area</label>
              <p className="text-gray-900">{currentOpp.assigned_practice_area}</p>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-gray-500">Posted Date</label>
            <p className="text-gray-900">{formatDate(currentOpp.posted_date)}</p>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-500">Response Deadline</label>
            <p className={`text-gray-900 ${urgencyClass}`}>
              {formatDate(currentOpp.response_deadline)}
              {days !== null && days >= 0 && (
                <span className="ml-2 text-sm">({days} days remaining)</span>
              )}
            </p>
          </div>

          {currentOpp.set_aside && (
            <div>
              <label className="text-sm font-medium text-gray-500">Set Aside</label>
              <p className="text-gray-900">{currentOpp.set_aside}</p>
            </div>
          )}

          {currentOpp.ptype && (
            <div>
              <label className="text-sm font-medium text-gray-500">Type</label>
              <p className="text-gray-900">{currentOpp.ptype}</p>
            </div>
          )}
        </div>

        {/* Links */}
        {currentOpp.sam_link && (
          <div className="mt-4">
            <a
              href={currentOpp.sam_link}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:text-primary-700 underline"
            >
              View on SAM.gov →
            </a>
          </div>
        )}
      </div>

      {/* Description */}
      {currentOpp.summary_description && (
        <div className="card mb-6">
          <h3 className="text-lg font-semibold mb-3">Description</h3>
          <div
            className="text-gray-700 prose max-w-none"
            dangerouslySetInnerHTML={{ __html: currentOpp.summary_description }}
          />
        </div>
      )}

      {/* AI Justification */}
      {currentOpp.justification && (
        <div className="card mb-6 bg-blue-50 border-blue-200">
          <h3 className="text-lg font-semibold mb-3 text-blue-900">AI Fit Analysis</h3>
          <p className="text-blue-800">{currentOpp.justification}</p>
        </div>
      )}

      {/* Workflow Controls */}
      <div className="mb-6">
        <WorkflowControls opportunity={currentOpp} onUpdate={setLocalOpportunity} />
      </div>

      {/* GovWin Matches */}
      {matches && matches.length > 0 && (
        <div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            GovWin Matches ({matches.length})
          </h2>
          {matches.length > 1 && (
            <div className="card mb-4 bg-blue-50 border-blue-200">
              <p className="text-sm text-blue-800">
                <strong>Multiple matches found.</strong> Review each match and confirm the correct ones or remove any that don't match.
              </p>
            </div>
          )}
          <div className="space-y-6">
            {matches.map((match) => (
              <MatchWithContracts
                key={match.id}
                match={match}
                opportunityId={opportunityId}
                onStatusChange={handleStatusChange}
                onDelete={handleDeleteMatch}
              />
            ))}
          </div>
        </div>
      )}

      {matches && matches.length === 0 && currentOpp.fit_score && currentOpp.fit_score >= 6 && (
        <div className="card text-center py-8 bg-gray-50">
          <div className="text-4xl mb-3">🔍</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No GovWin Matches Yet</h3>
          <p className="text-gray-600">
            This high-scoring opportunity (fit score: {currentOpp.fit_score}) will be automatically searched in GovWin.
          </p>
        </div>
      )}
    </div>
  );
}
