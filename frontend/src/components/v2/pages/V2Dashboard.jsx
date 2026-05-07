import React, { useState, useEffect } from 'react';
import V2Layout from '../V2Layout';
import { measurementsV2Api } from '../../../services/apiV2';

const V2Dashboard = () => {
  const [stats, setStats] = useState({ pending: 0, recent: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await measurementsV2Api.list({ status: 'pending', page_size: 5 });
        setStats({ pending: res.total ?? res.items?.length ?? 0, recent: res.items ?? [] });
      } catch {
        setStats({ pending: 0, recent: [] });
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  return (
    <V2Layout>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Dashboard</h1>
      {loading ? (
        <div className="animate-pulse h-24 bg-slate-200 rounded-xl" />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <p className="text-slate-500 text-sm font-medium">Pending Measurements</p>
            <p className="text-3xl font-bold text-blue-600 mt-1">{stats.pending}</p>
            <a href="/v2/measurements?status=pending" className="text-sm text-blue-600 mt-2 inline-block hover:underline">View all →</a>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 md:col-span-2">
            <p className="text-slate-500 text-sm font-medium mb-3">Recent Activity</p>
            {stats.recent.length === 0 ? (
              <p className="text-slate-400">No recent measurements</p>
            ) : (
              <ul className="space-y-2">
                {stats.recent.map((m) => (
                  <li key={m.id} className="flex justify-between text-sm">
                    <span className="text-slate-600">Measurement {m.id?.slice(0, 8)}...</span>
                    <span className="text-slate-400">{m.created_at ? new Date(m.created_at).toLocaleDateString() : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
    </V2Layout>
  );
};

export default V2Dashboard;
