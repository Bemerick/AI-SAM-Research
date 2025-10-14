import { Link, useLocation } from 'react-router-dom';

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path ? 'bg-primary-700' : 'hover:bg-primary-700';
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-primary-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="text-xl font-bold">
                SAM.gov Opportunity Manager
              </Link>
            </div>

            <div className="flex space-x-1">
              <Link
                to="/"
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/')}`}
              >
                All Opportunities
              </Link>
              <Link
                to="/high-scoring"
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${isActive('/high-scoring')}`}
              >
                High Scoring
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="w-full">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <p className="text-center text-sm text-gray-500">
            SAM.gov & GovWin Opportunity Management System
          </p>
        </div>
      </footer>
    </div>
  );
}
