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
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareEmails, setShareEmails] = useState('');
  const [senderName, setSenderName] = useState('');
  const [shareMessage, setShareMessage] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);

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

  // Mutation for toggling follow status
  const toggleFollowMutation = useMutation({
    mutationFn: () => samOpportunitiesAPI.toggleFollow(opportunityId),
    onSuccess: (updatedOpp) => {
      setLocalOpportunity(updatedOpp);
      queryClient.invalidateQueries({ queryKey: ['sam-opportunity', opportunityId] });
      queryClient.invalidateQueries({ queryKey: ['sam-opportunities'] });
    },
  });

  const handleToggleFollow = () => {
    toggleFollowMutation.mutate();
  };

  // Mutation for sharing via email
  const shareEmailMutation = useMutation({
    mutationFn: ({ emails, senderName, message, attachments }: {
      emails: string;
      senderName?: string;
      message?: string;
      attachments?: File[];
    }) =>
      samOpportunitiesAPI.shareViaEmail(opportunityId, emails, senderName, message, attachments),
    onSuccess: (data) => {
      alert(data.message);
      setShowShareModal(false);
      setShareEmails('');
      setSenderName('');
      setShareMessage('');
      setAttachments([]);
    },
    onError: (error: any) => {
      alert(`Failed to send email: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleShareEmail = () => {
    setShowShareModal(true);
  };

  const handleSendShare = () => {
    // Basic validation
    if (!shareEmails.trim()) {
      alert('Please enter at least one email address');
      return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const emails = shareEmails.split(',').map(e => e.trim()).filter(e => e.length > 0);
    const invalidEmails = emails.filter(e => !emailRegex.test(e));
    if (invalidEmails.length > 0) {
      alert(`Invalid email address(es): ${invalidEmails.join(', ')}`);
      return;
    }

    shareEmailMutation.mutate({
      emails: shareEmails,
      senderName: senderName || undefined,
      message: shareMessage || undefined,
      attachments: attachments.length > 0 ? attachments : undefined
    });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setAttachments(Array.from(e.target.files));
    }
  };

  const handleRemoveAttachment = (index: number) => {
    setAttachments(attachments.filter((_, i) => i !== index));
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
            <div className="flex items-center gap-2 mb-2">
              <p className="text-gray-600">Notice ID: {currentOpp.notice_id}</p>
              {currentOpp.is_amendment !== null && currentOpp.is_amendment > 0 && (
                <span className="badge badge-primary text-xs" title={`Amendment #${currentOpp.is_amendment}`}>
                  Updated
                </span>
              )}
              {currentOpp.superseded_by_notice_id && (
                <span className="badge badge-warning text-xs" title={`Superseded by notice: ${currentOpp.superseded_by_notice_id}`}>
                  Superseded
                </span>
              )}
            </div>
            {currentOpp.original_notice_id && currentOpp.is_amendment > 0 && (
              <p className="text-sm text-gray-500">
                Amendment of: <span className="font-mono">{currentOpp.original_notice_id}</span>
              </p>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleToggleFollow}
              className="text-3xl hover:scale-110 transition-transform"
              title={currentOpp.is_followed ? "Unfollow opportunity" : "Follow opportunity"}
            >
              {currentOpp.is_followed ? '⭐' : '☆'}
            </button>
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

      {/* Share via Email Modal */}
      {showShareModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Share Opportunity via Email</h3>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Name (Optional)
                </label>
                <input
                  type="text"
                  value={senderName}
                  onChange={(e) => setSenderName(e.target.value)}
                  placeholder="John Doe"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Recipient Email(s) *
                </label>
                <input
                  type="text"
                  value={shareEmails}
                  onChange={(e) => setShareEmails(e.target.value)}
                  placeholder="email@example.com, another@example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <p className="text-xs text-gray-500 mt-1">Separate multiple emails with commas</p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Message / Notes (Optional)
                </label>
                <textarea
                  value={shareMessage}
                  onChange={(e) => setShareMessage(e.target.value)}
                  placeholder="Add a personal message or notes about this opportunity..."
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <p className="text-xs text-gray-500 mt-1">This message will be included in the email</p>
              </div>

              <div className="mb-6">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Attachments (Optional)
                </label>
                <input
                  type="file"
                  multiple
                  onChange={handleFileChange}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                />
                <p className="text-xs text-gray-500 mt-1">You can select multiple files</p>

                {attachments.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {attachments.map((file, index) => (
                      <div key={index} className="flex items-center justify-between bg-gray-50 px-3 py-2 rounded-md">
                        <span className="text-sm text-gray-700 truncate flex-1">
                          📎 {file.name} ({(file.size / 1024).toFixed(1)} KB)
                        </span>
                        <button
                          onClick={() => handleRemoveAttachment(index)}
                          className="text-red-600 hover:text-red-700 ml-2 text-sm"
                        >
                          Remove
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => {
                    setShowShareModal(false);
                    setShareEmails('');
                    setSenderName('');
                    setShareMessage('');
                    setAttachments([]);
                  }}
                  className="btn btn-secondary"
                  disabled={shareEmailMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSendShare}
                  disabled={shareEmailMutation.isPending}
                  className="btn btn-primary"
                >
                  {shareEmailMutation.isPending ? (
                    <>
                      <span className="inline-block animate-spin mr-2">⏳</span>
                      Sending...
                    </>
                  ) : (
                    '📧 Send Email'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
