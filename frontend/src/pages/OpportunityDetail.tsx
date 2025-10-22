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

  const handleShareEmail = () => {
    const opp = currentOpp;
    if (!opp) return;

    // Get the current page URL for the detail link
    const detailUrl = window.location.href;

    // Build HTML email body
    const emailSubject = `SAM Opportunity: ${opp.title}`;

    const emailBody = `
<!DOCTYPE html>
<html>
<head>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; }
    .header { background-color: #2563eb; color: white; padding: 20px; text-align: center; }
    .header h1 { margin: 0; font-size: 24px; }
    .card { background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 20px 0; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px; }
    .info-item { margin-bottom: 10px; }
    .info-label { font-weight: bold; color: #6b7280; font-size: 14px; }
    .info-value { color: #111827; margin-top: 5px; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 14px; font-weight: 600; }
    .badge-score { background-color: #dbeafe; color: #1e40af; }
    .summary { background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 15px; margin: 15px 0; }
    .btn { display: inline-block; background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 10px 10px 0; }
    .btn:hover { background-color: #1d4ed8; }
    .footer { text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; padding: 20px; border-top: 1px solid #e5e7eb; }
  </style>
</head>
<body>
  <div class="header">
    <h1>SAM.gov Opportunity</h1>
  </div>

  <div class="card">
    <h2 style="margin-top: 0; color: #111827;">${opp.title}</h2>
    <p style="color: #6b7280;">Notice ID: ${opp.notice_id}</p>

    ${opp.fit_score ? `<div style="margin: 15px 0;"><span class="badge badge-score">Fit Score: ${opp.fit_score}/10</span></div>` : ''}

    <div class="info-grid">
      <div class="info-item">
        <div class="info-label">Department</div>
        <div class="info-value">${opp.department || 'N/A'}</div>
      </div>

      ${opp.solicitation_number ? `
      <div class="info-item">
        <div class="info-label">Solicitation Number</div>
        <div class="info-value">${opp.solicitation_number}</div>
      </div>
      ` : ''}

      <div class="info-item">
        <div class="info-label">NAICS Code</div>
        <div class="info-value">${opp.naics_code || 'N/A'}</div>
      </div>

      ${opp.assigned_practice_area ? `
      <div class="info-item">
        <div class="info-label">Practice Area</div>
        <div class="info-value">${opp.assigned_practice_area}</div>
      </div>
      ` : ''}

      <div class="info-item">
        <div class="info-label">Posted Date</div>
        <div class="info-value">${formatDate(opp.posted_date)}</div>
      </div>

      <div class="info-item">
        <div class="info-label">Response Deadline</div>
        <div class="info-value">${formatDate(opp.response_deadline)}</div>
      </div>

      ${opp.set_aside ? `
      <div class="info-item">
        <div class="info-label">Set Aside</div>
        <div class="info-value">${opp.set_aside}</div>
      </div>
      ` : ''}

      ${opp.ptype ? `
      <div class="info-item">
        <div class="info-label">Type</div>
        <div class="info-value">${opp.ptype}</div>
      </div>
      ` : ''}

      ${opp.place_of_performance_city || opp.place_of_performance_state ? `
      <div class="info-item">
        <div class="info-label">Place of Performance</div>
        <div class="info-value">${[opp.place_of_performance_city, opp.place_of_performance_state].filter(Boolean).join(', ')}</div>
      </div>
      ` : ''}
    </div>

    ${opp.summary_description ? `
    <div class="summary">
      <strong style="color: #1e40af;">Summary:</strong>
      <p style="margin: 10px 0 0 0;">${opp.summary_description}</p>
    </div>
    ` : ''}

    <div style="margin-top: 25px;">
      ${opp.sam_link ? `<a href="${opp.sam_link}" class="btn">View on SAM.gov</a>` : ''}
      <a href="${detailUrl}" class="btn">View Full Details</a>
    </div>
  </div>

  <div class="footer">
    <p>This opportunity was shared from the SAM Opportunity Management System</p>
  </div>
</body>
</html>`.trim();

    // Create mailto link
    const mailtoLink = `mailto:?subject=${encodeURIComponent(emailSubject)}&body=${encodeURIComponent(emailBody)}`;

    // Open email client
    window.location.href = mailtoLink;
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
              onClick={handleShareEmail}
              className="btn btn-secondary"
              title="Share this opportunity via email"
            >
              📧 Share
            </button>
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

      {/* AI-Generated Summary */}
      {currentOpp.summary_description && (
        <div className="card mb-6 bg-blue-50 border-blue-200">
          <h3 className="text-lg font-semibold mb-3 text-blue-900">AI Summary</h3>
          <p className="text-blue-800">{currentOpp.summary_description}</p>
        </div>
      )}

      {/* AI Justification */}
      {currentOpp.justification && (
        <div className="card mb-6 bg-green-50 border-green-200">
          <h3 className="text-lg font-semibold mb-3 text-green-900">AI Fit Analysis</h3>
          <p className="text-green-800">{currentOpp.justification}</p>
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
