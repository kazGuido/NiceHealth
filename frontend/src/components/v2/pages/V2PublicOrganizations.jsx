import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { publicApi } from '../../../services/apiV2';

const V2PublicOrganizations = () => {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    publicApi.getOrganizations()
      .then((data) => setOrgs(Array.isArray(data) ? data : data.items || []))
      .catch(() => setOrgs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 p-6">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-slate-800 mb-6">Organizations</h1>
        <Link to="/v2/discover/locations" className="text-blue-600 hover:underline mb-4 inline-block">View all locations</Link>
        {loading ? (
          <div className="animate-pulse h-32 bg-slate-200 rounded-xl" />
        ) : orgs.length === 0 ? (
          <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500">
            No organizations
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {orgs.map((org) => (
              <Link key={org.id} to={`/v2/discover/locations?org=${org.id}`} className="block p-6 bg-white rounded-xl border border-slate-200 hover:border-blue-300">
                <h3 className="font-semibold text-slate-800">{org.name || org.brand_name || 'Unnamed'}</h3>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default V2PublicOrganizations;
