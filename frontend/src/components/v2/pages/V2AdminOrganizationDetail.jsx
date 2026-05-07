import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import V2Layout from '../V2Layout';
import { organizationsAdminApi } from '../../../services/apiV2';

const V2AdminOrganizationDetail = () => {
  const { id } = useParams();
  const [org, setOrg] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id && id !== 'new') {
      organizationsAdminApi.get(id).then(setOrg).catch(() => setOrg(null)).finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [id]);

  if (id === 'new') {
    return (
      <V2Layout>
        <h1 className="text-2xl font-bold text-slate-800 mb-6">New Organization</h1>
        <div className="bg-white p-6 rounded-xl border border-slate-200">
          <p className="text-slate-500">Organization creation form – connect to backend POST /v2/admin/organizations/</p>
        </div>
      </V2Layout>
    );
  }

  if (loading || !org) {
    return (
      <V2Layout>
        <div className="animate-pulse h-48 bg-slate-200 rounded-xl" />
      </V2Layout>
    );
  }

  return (
    <V2Layout>
      <div className="mb-6 flex items-center gap-4">
        <Link to="/v2/admin/organizations" className="text-slate-500 hover:text-slate-700">← Back</Link>
        <h1 className="text-2xl font-bold text-slate-800">{org.name || 'Organization'}</h1>
      </div>
      <div className="bg-white p-6 rounded-xl border border-slate-200 space-y-4">
        <p><span className="text-slate-500">ID:</span> {org.id}</p>
        <p><span className="text-slate-500">Primary User:</span> {org.primary_user_id || '—'}</p>
      </div>
    </V2Layout>
  );
};

export default V2AdminOrganizationDetail;
