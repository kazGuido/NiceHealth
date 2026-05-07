import React, { useState, useEffect } from 'react';
import V2Layout from '../V2Layout';
import { retailInvitesApi } from '../../../services/apiV2';

const V2Invites = () => {
  const [invites, setInvites] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    retailInvitesApi.list()
      .then((data) => setInvites(Array.isArray(data) ? data : data.items || []))
      .catch(() => setInvites([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <V2Layout>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Retail User Invites</h1>
      <div className="bg-white p-6 rounded-xl border border-slate-200 mb-6">
        <p className="text-slate-500">Invite form – retailInvitesApi.invite(email)</p>
      </div>
      {loading ? (
        <div className="animate-pulse h-24 bg-slate-200 rounded-xl" />
      ) : invites.length === 0 ? (
        <p className="text-slate-500">No invites yet</p>
      ) : (
        <ul className="space-y-2">
          {invites.map((i) => (
            <li key={i.id} className="flex justify-between p-3 bg-slate-50 rounded-lg">
              <span>{i.email}</span>
              <span className="text-slate-500 text-sm">{i.status || 'pending'}</span>
            </li>
          ))}
        </ul>
      )}
    </V2Layout>
  );
};

export default V2Invites;
