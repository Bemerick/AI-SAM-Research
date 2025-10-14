import { useState } from 'react';
import { samOpportunitiesAPI } from '../services/api';
import type { SAMOpportunity, ReviewStatus } from '../types';
import { REVIEW_STATUSES } from '../types';

interface WorkflowControlsProps {
  opportunity: SAMOpportunity;
  onUpdate: (updated: SAMOpportunity) => void;
}

export default function WorkflowControls({ opportunity, onUpdate }: WorkflowControlsProps) {
  const [reviewForBid, setReviewForBid] = useState<ReviewStatus>(opportunity.review_for_bid as ReviewStatus);
  const [recommendBid, setRecommendBid] = useState<ReviewStatus>(opportunity.recommend_bid as ReviewStatus);
  const [reviewComments, setReviewComments] = useState(opportunity.review_comments || '');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  const handleSave = async () => {
    setSaving(true);
    setMessage('');

    try {
      const updated = await samOpportunitiesAPI.update(opportunity.id, {
        review_for_bid: reviewForBid,
        recommend_bid: recommendBid,
        review_comments: reviewComments || undefined,
        reviewed_by: 'current.user@company.com', // TODO: Get from auth context
      });

      onUpdate(updated);
      setMessage('Saved successfully!');
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      console.error('Error saving:', error);
      setMessage('Error saving. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    reviewForBid !== opportunity.review_for_bid ||
    recommendBid !== opportunity.recommend_bid ||
    (reviewComments || '') !== (opportunity.review_comments || '');

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">Workflow Review</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="label">Review For Bid</label>
          <select
            className="select"
            value={reviewForBid}
            onChange={(e) => setReviewForBid(e.target.value as ReviewStatus)}
          >
            {REVIEW_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label">Recommend Bid</label>
          <select
            className="select"
            value={recommendBid}
            onChange={(e) => setRecommendBid(e.target.value as ReviewStatus)}
          >
            {REVIEW_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mb-4">
        <label className="label">Review Comments</label>
        <textarea
          className="textarea"
          value={reviewComments}
          onChange={(e) => setReviewComments(e.target.value)}
          placeholder="Add your review notes here..."
          rows={4}
        />
      </div>

      {opportunity.reviewed_by && (
        <div className="text-sm text-gray-500 mb-4">
          Last reviewed by: {opportunity.reviewed_by}
          {opportunity.reviewed_at && ` on ${new Date(opportunity.reviewed_at).toLocaleDateString()}`}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          className="btn btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Review'}
        </button>

        {message && (
          <span className={`text-sm ${message.includes('Error') ? 'text-red-600' : 'text-green-600'}`}>
            {message}
          </span>
        )}
      </div>
    </div>
  );
}
