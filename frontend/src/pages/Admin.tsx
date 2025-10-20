import { useState } from 'react';
import { fetchSAMOpportunitiesByDate } from '../services/api';

export default function Admin() {
  const [selectedDate, setSelectedDate] = useState(() => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  });
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<{
    message: string;
    fetched_count: number;
    stored_count: number;
    duplicate_count: number;
    error_count: number;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFetch = async () => {
    if (!selectedDate) {
      setError('Please select a date');
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetchSAMOpportunitiesByDate(selectedDate);
      setResult(response);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch opportunities');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Admin Panel</h1>
        <p className="mt-2 text-sm text-gray-600">
          Manage SAM.gov data fetching and system configuration
        </p>
      </div>

      {/* Fetch SAM Data by Date Section */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Fetch SAM.gov Opportunities by Date
        </h2>
        <p className="text-sm text-gray-600 mb-6">
          Fetch opportunities from SAM.gov for a specific posted date. The system will
          automatically skip duplicates using the existing duplicate checking logic.
        </p>

        <div className="space-y-4">
          {/* Date Picker */}
          <div>
            <label htmlFor="fetch-date" className="block text-sm font-medium text-gray-700 mb-2">
              Posted Date
            </label>
            <input
              type="date"
              id="fetch-date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="block w-full max-w-xs px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              disabled={isLoading}
            />
          </div>

          {/* Fetch Button */}
          <div>
            <button
              onClick={handleFetch}
              disabled={isLoading || !selectedDate}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <>
                  <svg
                    className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    ></circle>
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    ></path>
                  </svg>
                  Fetching...
                </>
              ) : (
                'Fetch Opportunities'
              )}
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-md bg-red-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-red-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">Error</h3>
                  <div className="mt-2 text-sm text-red-700">{error}</div>
                </div>
              </div>
            </div>
          )}

          {/* Success Result */}
          {result && (
            <div className="rounded-md bg-green-50 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg
                    className="h-5 w-5 text-green-400"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div className="ml-3 flex-1">
                  <h3 className="text-sm font-medium text-green-800">
                    {result.message}
                  </h3>
                  <div className="mt-3 text-sm text-green-700">
                    <dl className="grid grid-cols-2 gap-4">
                      <div>
                        <dt className="font-semibold">Fetched:</dt>
                        <dd>{result.fetched_count}</dd>
                      </div>
                      <div>
                        <dt className="font-semibold">Stored:</dt>
                        <dd className="text-green-900 font-bold">{result.stored_count}</dd>
                      </div>
                      <div>
                        <dt className="font-semibold">Duplicates:</dt>
                        <dd>{result.duplicate_count}</dd>
                      </div>
                      <div>
                        <dt className="font-semibold">Errors:</dt>
                        <dd className={result.error_count > 0 ? 'text-red-600 font-bold' : ''}>
                          {result.error_count}
                        </dd>
                      </div>
                    </dl>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Info Box */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg
              className="h-5 w-5 text-blue-400"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 20 20"
              fill="currentColor"
            >
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div className="ml-3 flex-1">
            <h3 className="text-sm font-medium text-blue-800">Information</h3>
            <div className="mt-2 text-sm text-blue-700">
              <ul className="list-disc list-inside space-y-1">
                <li>Fetches opportunities for all configured NAICS codes (15 codes)</li>
                <li>Automatically skips duplicates based on notice_id</li>
                <li>New opportunities will have a fit_score of 0 (unscored)</li>
                <li>Run the AI Analyzer cron job to score the new opportunities</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
