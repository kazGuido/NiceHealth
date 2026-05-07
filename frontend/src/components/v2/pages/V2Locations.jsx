import React, { useState, useEffect } from 'react';
import V2Layout from '../V2Layout';
import { locationsApi } from '../../../services/apiV2';

const V2Locations = () => {
  const [locations, setLocations] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    locationsApi.list()
      .then((data) => setLocations(Array.isArray(data) ? data : data.items || []))
      .catch(() => setLocations([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <V2Layout>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Locations</h1>
      {loading ? (
        <div className="animate-pulse h-32 bg-slate-200 rounded-xl" />
      ) : locations.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500">
          No locations. Create one to manage your measurement sites.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {locations.map((loc) => (
            <div key={loc.id} className="p-6 bg-white rounded-xl border border-slate-200">
              <h3 className="font-semibold text-slate-800">{loc.name || 'Unnamed'}</h3>
              <p className="text-sm text-slate-500 mt-1">{loc.address || '—'}</p>
            </div>
          ))}
        </div>
      )}
    </V2Layout>
  );
};

export default V2Locations;
