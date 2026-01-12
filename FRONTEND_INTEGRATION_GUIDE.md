# Frontend Integration Guide

## Quick Start: Add Export & Bulk Operations to Your Dashboard

### 1. Add Export Buttons

#### Option A: Simple Button Implementation
```typescript
// In your DashboardConnected.tsx or any component

function ExportButtons({ projectId }: { projectId: string }) {
  const API_BASE = 'https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca';
  
  const handleExport = (type: string) => {
    const url = `${API_BASE}/projects/${projectId}/export/${type}`;
    window.open(url, '_blank');
  };

  return (
    <div className="flex gap-2">
      <button 
        onClick={() => handleExport('pages')}
        className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
      >
        📄 Export Pages (CSV)
      </button>
      
      <button 
        onClick={() => handleExport('opportunities')}
        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
      >
        💡 Export Opportunities (CSV)
      </button>
      
      <button 
        onClick={() => handleExport('anchors')}
        className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
      >
        🔗 Export Anchor Texts (CSV)
      </button>
      
      <button 
        onClick={() => handleExport('report')}
        className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700"
      >
        📊 Export Report (HTML)
      </button>
    </div>
  );
}
```

#### Option B: Dropdown Menu Implementation
```typescript
import { Download, ChevronDown } from 'lucide-react';

function ExportMenu({ projectId }: { projectId: string }) {
  const [isOpen, setIsOpen] = useState(false);
  const API_BASE = 'https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca';
  
  const handleExport = (type: string) => {
    const url = `${API_BASE}/projects/${projectId}/export/${type}`;
    window.open(url, '_blank');
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
      >
        <Download size={16} />
        Export
        <ChevronDown size={14} />
      </button>
      
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
          <button
            onClick={() => handleExport('pages')}
            className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b"
          >
            📄 Pages (CSV)
          </button>
          <button
            onClick={() => handleExport('opportunities')}
            className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b"
          >
            💡 Opportunities (CSV)
          </button>
          <button
            onClick={() => handleExport('anchors')}
            className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b"
          >
            🔗 Anchor Texts (CSV)
          </button>
          <button
            onClick={() => handleExport('report')}
            className="w-full text-left px-4 py-2 hover:bg-gray-50"
          >
            📊 Full Report (HTML/PDF)
          </button>
        </div>
      )}
    </div>
  );
}
```

### 2. Add Bulk Operations to Opportunities Table

```typescript
// BulkOperationsPanel.tsx

import { useState } from 'react';
import { Check, X, CheckCircle } from 'lucide-react';

interface BulkOperationsPanelProps {
  opportunities: any[];
  projectId: string;
  onUpdate: () => void;
}

function BulkOperationsPanel({ opportunities, projectId, onUpdate }: BulkOperationsPanelProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSelectAll = () => {
    if (selectedIds.length === opportunities.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(opportunities.map(o => o.id));
    }
  };

  const handleToggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleBulkUpdate = async (status: string) => {
    if (selectedIds.length === 0) {
      alert('Please select opportunities first');
      return;
    }

    try {
      setLoading(true);
      const API_BASE = 'https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca';
      
      const response = await fetch(`${API_BASE}/opportunities/bulk-update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          opportunity_ids: selectedIds,
          status: status
        })
      });

      const data = await response.json();
      
      if (data.success) {
        alert(`Updated ${selectedIds.length} opportunities to ${status}`);
        setSelectedIds([]);
        onUpdate(); // Refresh data
      } else {
        alert(`Error: ${data.error}`);
      }
    } catch (error: any) {
      alert(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Bulk Actions Bar */}
      <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={selectedIds.length === opportunities.length}
            onChange={handleSelectAll}
            className="w-4 h-4"
          />
          <span className="text-sm text-gray-600">
            {selectedIds.length} of {opportunities.length} selected
          </span>
        </div>

        {selectedIds.length > 0 && (
          <div className="flex gap-2">
            <button
              onClick={() => handleBulkUpdate('accepted')}
              disabled={loading}
              className="flex items-center gap-1 bg-green-600 text-white px-3 py-1.5 rounded text-sm hover:bg-green-700 disabled:opacity-50"
            >
              <Check size={14} />
              Accept ({selectedIds.length})
            </button>
            
            <button
              onClick={() => handleBulkUpdate('implemented')}
              disabled={loading}
              className="flex items-center gap-1 bg-blue-600 text-white px-3 py-1.5 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              <CheckCircle size={14} />
              Mark Done ({selectedIds.length})
            </button>
            
            <button
              onClick={() => handleBulkUpdate('rejected')}
              disabled={loading}
              className="flex items-center gap-1 bg-red-600 text-white px-3 py-1.5 rounded text-sm hover:bg-red-700 disabled:opacity-50"
            >
              <X size={14} />
              Reject ({selectedIds.length})
            </button>
          </div>
        )}
      </div>

      {/* Opportunities Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b">
            <tr>
              <th className="w-10 px-4 py-3"></th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-600 uppercase">From</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-600 uppercase">To</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-gray-600 uppercase">Anchor</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-600 uppercase">Type</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-600 uppercase">Priority</th>
              <th className="text-center px-4 py-3 text-xs font-medium text-gray-600 uppercase">Status</th>
            </tr>
          </thead>
          <tbody>
            {opportunities.map((opp) => (
              <tr key={opp.id} className="border-b hover:bg-gray-50">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(opp.id)}
                    onChange={() => handleToggleSelect(opp.id)}
                    className="w-4 h-4"
                  />
                </td>
                <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">{opp.from_url}</td>
                <td className="px-4 py-3 text-sm text-gray-600 max-w-xs truncate">{opp.to_url}</td>
                <td className="px-4 py-3 text-sm text-gray-900">{opp.anchor}</td>
                <td className="px-4 py-3 text-center">
                  <span className="text-xs px-2 py-1 rounded bg-blue-100 text-blue-700">
                    {opp.type}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`text-xs px-2 py-1 rounded ${
                    opp.priority === 'High' ? 'bg-red-100 text-red-700' :
                    opp.priority === 'Medium' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {opp.priority}
                  </span>
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`text-xs px-2 py-1 rounded ${
                    opp.status === 'implemented' ? 'bg-green-100 text-green-700' :
                    opp.status === 'accepted' ? 'bg-blue-100 text-blue-700' :
                    opp.status === 'rejected' ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {opp.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default BulkOperationsPanel;
```

### 3. Add to Your Dashboard

```typescript
// In DashboardConnected.tsx

import BulkOperationsPanel from './BulkOperationsPanel';
import ExportMenu from './ExportMenu';

export function DashboardConnected({ projectId }: DashboardConnectedProps) {
  const { data: opportunities, loading, refetch } = useApiData(
    `/projects/${projectId}/opportunities`, 
    [projectId]
  );

  return (
    <div className="dashboard">
      {/* Header with Export Button */}
      <div className="flex justify-between items-center p-6">
        <h1>Dashboard</h1>
        <ExportMenu projectId={projectId} />
      </div>

      {/* ... other dashboard components ... */}

      {/* Opportunities with Bulk Operations */}
      <div className="p-6">
        <h2 className="text-xl font-semibold mb-4">
          Internal Linking Opportunities
        </h2>
        <BulkOperationsPanel
          opportunities={opportunities || []}
          projectId={projectId}
          onUpdate={refetch}
        />
      </div>
    </div>
  );
}
```

### 4. Add Status Filter Tabs (Optional)

```typescript
function OpportunitiesWithFilters({ projectId }: { projectId: string }) {
  const [activeStatus, setActiveStatus] = useState('pending');
  const { data: opportunities, loading } = useApiData(
    `/projects/${projectId}/opportunities/${activeStatus}`,
    [projectId, activeStatus]
  );

  const statuses = [
    { value: 'pending', label: 'Pending', color: 'gray' },
    { value: 'accepted', label: 'Accepted', color: 'blue' },
    { value: 'implemented', label: 'Implemented', color: 'green' },
    { value: 'rejected', label: 'Rejected', color: 'red' },
  ];

  return (
    <div>
      {/* Status Tabs */}
      <div className="flex gap-2 mb-4">
        {statuses.map(status => (
          <button
            key={status.value}
            onClick={() => setActiveStatus(status.value)}
            className={`px-4 py-2 rounded ${
              activeStatus === status.value
                ? `bg-${status.color}-600 text-white`
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            {status.label}
          </button>
        ))}
      </div>

      {/* Opportunities Table */}
      <BulkOperationsPanel
        opportunities={opportunities || []}
        projectId={projectId}
        onUpdate={() => {}}
      />
    </div>
  );
}
```

### 5. Update Your API Hook (useApi.ts)

```typescript
// Add bulk update method to your API helper

export const api = {
  // ... existing methods ...

  bulkUpdateOpportunities: async (opportunityIds: string[], status: string) => {
    const response = await fetch(`${API_BASE}/opportunities/bulk-update`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        opportunity_ids: opportunityIds,
        status: status
      })
    });
    return await response.json();
  },

  getOpportunitiesByStatus: async (projectId: string, status: string) => {
    const response = await fetch(
      `${API_BASE}/projects/${projectId}/opportunities/${status}`
    );
    return await response.json();
  },

  exportPages: (projectId: string) => {
    window.open(`${API_BASE}/projects/${projectId}/export/pages`, '_blank');
  },

  exportOpportunities: (projectId: string) => {
    window.open(`${API_BASE}/projects/${projectId}/export/opportunities`, '_blank');
  },

  exportAnchors: (projectId: string) => {
    window.open(`${API_BASE}/projects/${projectId}/export/anchors`, '_blank');
  },

  exportReport: (projectId: string) => {
    window.open(`${API_BASE}/projects/${projectId}/export/report`, '_blank');
  },
};
```

---

## Testing Your New Features

### Test Export Endpoints:
```bash
# Pages CSV
curl "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca/projects/PROJECT_ID/export/pages" -o pages.csv

# Opportunities CSV
curl "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca/projects/PROJECT_ID/export/opportunities" -o opportunities.csv

# Anchor Texts CSV
curl "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca/projects/PROJECT_ID/export/anchors" -o anchors.csv

# HTML Report
curl "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca/projects/PROJECT_ID/export/report" -o report.html
```

### Test Bulk Update:
```bash
curl -X POST "https://YOUR_PROJECT.supabase.co/functions/v1/make-server-4180e2ca/opportunities/bulk-update" \
  -H "Content-Type: application/json" \
  -d '{
    "opportunity_ids": ["id1", "id2", "id3"],
    "status": "accepted"
  }'
```

---

## Environment Variables

Make sure to update your API base URL:

```typescript
// utils/api.ts or similar
const SUPABASE_PROJECT_ID = 'your-project-id'; // From Supabase dashboard
export const API_BASE = `https://${SUPABASE_PROJECT_ID}.supabase.co/functions/v1/make-server-4180e2ca`;
```

Or use environment variables:

```typescript
// .env
VITE_API_BASE=https://your-project.supabase.co/functions/v1/make-server-4180e2ca
```

```typescript
// In your code
const API_BASE = import.meta.env.VITE_API_BASE;
```

---

## Next Steps

1. **Copy the components above** into your project
2. **Replace `YOUR_PROJECT`** with your actual Supabase project ID
3. **Add the export menu** to your dashboard header
4. **Replace the opportunities table** with the BulkOperationsPanel
5. **Test the exports** by clicking the buttons
6. **Test bulk operations** by selecting opportunities and clicking actions

That's it! Your dashboard now has full export and bulk operations support! 🎉
