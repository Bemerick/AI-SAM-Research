import type { GovWinContract } from '../types';
import { formatDate } from '../utils/formatters';

interface ContractCardProps {
  contract: GovWinContract;
}

export default function ContractCard({ contract }: ContractCardProps) {
  // Format value in thousands
  const formatValueInK = (value: number | null) => {
    if (!value) return 'N/A';
    const valueInK = value / 1000;
    return `$${valueInK.toFixed(0)}K`;
  };

  return (
    <div className="card border-l-4 border-green-500">
      {/* Header with Contract Number and Title */}
      <div className="mb-4">
        <div className="flex justify-between items-start">
          <div className="flex-1">
            {contract.contract_number && (
              <div className="text-xs font-semibold text-gray-500 mb-1">
                Contract Number
              </div>
            )}
            <h5 className="text-md font-bold text-gray-900 mb-2">
              {contract.contract_number || 'N/A'}
            </h5>
          </div>
        </div>

        {contract.title && (
          <div>
            <div className="text-xs font-semibold text-gray-500 mb-1">
              Contract Title
            </div>
            <p className="text-sm text-gray-900">{contract.title}</p>
          </div>
        )}
      </div>

      {/* Contract Details Grid */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        {/* Vendor */}
        <div>
          <div className="text-xs font-semibold text-gray-500 mb-1">Vendor</div>
          <div className="text-gray-900">{contract.vendor_name || 'N/A'}</div>
        </div>

        {/* Award Date */}
        <div>
          <div className="text-xs font-semibold text-gray-500 mb-1">Award Date</div>
          <div className="text-gray-900">
            {contract.award_date ? formatDate(contract.award_date) : 'N/A'}
          </div>
        </div>

        {/* Current Expiration Date */}
        <div>
          <div className="text-xs font-semibold text-gray-500 mb-1">Current Expiration Date</div>
          <div className="text-gray-900">
            {contract.end_date ? formatDate(contract.end_date) : 'N/A'}
          </div>
        </div>

        {/* Ultimate Expiration Date (placeholder - would need to be in raw_data) */}
        <div>
          <div className="text-xs font-semibold text-gray-500 mb-1">Ultimate Expiration Date</div>
          <div className="text-gray-900">
            {contract.end_date ? formatDate(contract.end_date) : 'N/A'}
          </div>
        </div>

        {/* Spend-to-date (placeholder - would need to be in raw_data) */}
        <div>
          <div className="text-xs font-semibold text-gray-500 mb-1">Spend-to-date</div>
          <div className="text-gray-900 font-semibold">N/A</div>
        </div>

        {/* Est. Value */}
        <div className="col-span-2">
          <div className="text-xs font-semibold text-gray-500 mb-1">Est. Value</div>
          <div className="text-lg font-bold text-green-600">
            {formatValueInK(contract.contract_value)}
          </div>
        </div>
      </div>

      {/* Description (if available) */}
      {contract.description && (
        <div className="bg-gray-50 border border-gray-200 rounded-md p-3 mt-4">
          <div className="text-xs font-semibold text-gray-700 mb-1">Description</div>
          <p className="text-sm text-gray-600">{contract.description}</p>
        </div>
      )}
    </div>
  );
}
