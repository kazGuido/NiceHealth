import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { publicApi } from '../../../services/apiV2';

const V2PublicLocations = () => {
  const [searchParams] = useSearchParams();
  const orgId = searchParams.get('org');
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = orgId ? { organization_id: orgId } : {};
    publicApi.getLocations(params)
      .then((data) => setLocations(Array.isArray(data) ? data : data.items || []))
      .catch(() => setLocations([]))
      .finally(() => setLoading(false));
  }, [orgId]);

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800 mb-6">Find a Measurement Location</h1>
        <Link to="/v2/discover/organizations" className="text-blue-600 hover:underline mb-4 inline-block">Browse organizations</Link>
        {loading ? (
          <div className="animate-pulse h-32 bg-slate-200 rounded-xl" />
        ) : locations.length === 0 ? (
          <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500">
            No locations found
          </div>
        ) : (
          <div className="space-y-4">
            {locations.map((loc) => (
              <div key={loc.id} className="p-6 bg-white rounded-xl border border-slate-200">
                <h3 className="font-semibold text-slate-800">{loc.name || 'Unnamed'}</h3>
                <p className="text-slate-500 text-sm mt-1">{loc.address || '—'}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default V2PublicLocations;
