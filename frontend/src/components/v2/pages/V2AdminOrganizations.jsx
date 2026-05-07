import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import V2Layout from '../V2Layout';
import { organizationsAdminApi } from '../../../services/apiV2';

const V2AdminOrganizations = () => {
  const [orgs, setOrgs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    organizationsAdminApi.list()
      .then((data) => setOrgs(Array.isArray(data) ? data : data.items || []))
      .catch(() => setOrgs([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <V2Layout>
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-slate-800">Organizations</h1>
        <Link to="/v2/admin/organizations/new" className="px-4 py-2 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700">
          Add Organization
        </Link>
      </div>
      {loading ? (
        <div className="animate-pulse h-32 bg-slate-200 rounded-xl" />
      ) : orgs.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500">
          No organizations yet. Create one to get started.
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {orgs.map((org) => (
            <Link
              key={org.id}
              to={`/v2/admin/organizations/${org.id}`}
              className="block p-6 bg-white rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition"
            >
              <h3 className="font-semibold text-slate-800">{org.name || 'Unnamed'}</h3>
              <p className="text-sm text-slate-500 mt-1">{org.primary_user_id ? 'Has primary user' : 'No primary user'}</p>
            </Link>
          ))}
        </div>
      )}
    </V2Layout>
  );
};

export default V2AdminOrganizations;
