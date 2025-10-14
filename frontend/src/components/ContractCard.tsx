import type { GovWinContract } from '../types';
import { formatCurrency, formatDate } from '../utils/formatters';

interface ContractCardProps {
  contract: GovWinContract;
}

export default function ContractCard({ contract }: ContractCardProps) {
  return (
    <div className="card border-l-4 border-green-500">
      <div className="flex justify-between items-start mb-3">
        <div className="flex-1">
          <h5 className="text-md font-semibold text-gray-900 mb-1">
            {contract.title || contract.contract_number || 'Untitled Contract'}
          </h5>
          {contract.contract_number && (
            <p className="text-sm text-gray-500">Contract #: {contract.contract_number}</p>
          )}
        </div>
        {contract.contract_value && (
          <div className="text-right">
            <div className="text-xl font-bold text-green-600">
              {formatCurrency(contract.contract_value)}
            </div>
            <div className="text-xs text-gray-500">Contract Value</div>
          </div>
        )}
      </div>

      <div className="space-y-2 mb-3">
        {contract.vendor_name && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-32">Vendor:</span>
            <span className="text-gray-900 font-medium">{contract.vendor_name}</span>
          </div>
        )}

        {contract.status && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-32">Status:</span>
            <span className="badge badge-primary">{contract.status}</span>
          </div>
        )}

        {contract.contract_type && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-32">Type:</span>
            <span className="text-gray-900">{contract.contract_type}</span>
          </div>
        )}

        {contract.award_date && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-32">Award Date:</span>
            <span className="text-gray-900">{formatDate(contract.award_date)}</span>
          </div>
        )}

        {contract.start_date && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-32">Start Date:</span>
            <span className="text-gray-900">{formatDate(contract.start_date)}</span>
          </div>
        )}

        {contract.end_date && (
          <div className="flex items-center text-sm">
            <span className="text-gray-500 w-32">End Date:</span>
            <span className="text-gray-900">{formatDate(contract.end_date)}</span>
          </div>
        )}
      </div>

      {contract.description && (
        <div className="bg-gray-50 border border-gray-200 rounded-md p-3 mt-3">
          <div className="text-xs font-semibold text-gray-700 mb-1">Description:</div>
          <p className="text-sm text-gray-600">{contract.description}</p>
        </div>
      )}
    </div>
  );
}
