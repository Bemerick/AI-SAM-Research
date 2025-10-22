import type { MatchWithDetails } from '../types';
import StatusBadge from './StatusBadge';
import { formatCurrency, formatDate, truncateText } from '../utils/formatters';

interface MatchCardProps {
  match: MatchWithDetails;
  onStatusChange?: (matchId: number, status: string) => void;
}

export default function MatchCard({ match, onStatusChange }: MatchCardProps) {
  const { govwin_opportunity } = match;

  // Generate GovWin URL based on prefix type
  const getGovWinUrl = (govwinId: string) => {
    // Check if ID starts with FBO prefix
    if (/^FBO/i.test(govwinId)) {
      // Strip FBO prefix to get numeric ID
      const numericId = govwinId.replace(/^FBO/i, '');
      return `https://iq.govwin.com/neo/fbo/view/${numericId}`;
    }
    // Default to opportunity URL (for OPP prefix or no prefix)
    // Strip OPP prefix if present to get numeric ID
    const numericId = govwinId.replace(/^OPP/i, '');
    return `https://iq.govwin.com/neo/opportunity/view/${numericId}`;
  };

  const govwinUrl = getGovWinUrl(govwin_opportunity.govwin_id);

  return (
    <div className="card card-hover">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h4 className="text-md font-semibold text-gray-900 mb-1">
            {govwin_opportunity.title || 'Untitled GovWin Opportunity'}
          </h4>
          <div className="flex items-center gap-2">
            <p className="text-sm text-gray-500">GovWin ID: {govwin_opportunity.govwin_id}</p>
            <a
              href={govwinUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary-600 hover:text-primary-700 text-sm underline"
              title="View in GovWin IQ"
            >
              View →
            </a>
          </div>
        </div>
        {match.ai_match_score !== null && (
          <div className="text-right">
            <div className="text-2xl font-bold text-primary-600">
              {match.ai_match_score.toFixed(1)}/10
            </div>
            <div className="text-xs text-gray-500">Match Score</div>
          </div>
        )}
      </div>

      <div className="space-y-2 mb-3">
        {govwin_opportunity.gov_entity && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Agency:</span>
            <span className="text-gray-900 font-medium">{govwin_opportunity.gov_entity}</span>
          </div>
        )}

        {govwin_opportunity.primary_naics && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">NAICS:</span>
            <span className="text-gray-900">{govwin_opportunity.primary_naics}</span>
          </div>
        )}

        {govwin_opportunity.value && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Value:</span>
            <span className="text-gray-900 font-semibold">{formatCurrency(govwin_opportunity.value)}</span>
          </div>
        )}

        {govwin_opportunity.post_date && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Posted:</span>
            <span className="text-gray-900">{formatDate(govwin_opportunity.post_date)}</span>
          </div>
        )}

        {govwin_opportunity.stage && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-24">Stage:</span>
            <span className="text-gray-900">{govwin_opportunity.stage}</span>
          </div>
        )}
      </div>

      {govwin_opportunity.description && (
        <p className="text-sm text-gray-600 mb-3">
          {truncateText(govwin_opportunity.description, 200)}
        </p>
      )}

      {match.ai_reasoning && (
        <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-3">
          <div className="text-xs font-semibold text-blue-900 mb-1">AI Analysis:</div>
          <p className="text-sm text-blue-800">{truncateText(match.ai_reasoning, 150)}</p>
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t">
        <div className="flex gap-2 items-center">
          <StatusBadge status={match.status} />
          <span className="badge badge-gray">{match.search_strategy}</span>
        </div>

        {onStatusChange && match.status === 'pending_review' && (
          <div className="flex gap-2">
            <button
              onClick={() => onStatusChange(match.id, 'confirmed')}
              className="btn btn-sm btn-success"
            >
              Confirm
            </button>
            <button
              onClick={() => onStatusChange(match.id, 'rejected')}
              className="btn btn-sm btn-danger"
            >
              Reject
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
