import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import V2Layout from '../V2Layout';
import { measurementsV2Api } from '../../../services/apiV2';

const V2Measurements = () => {
  const [searchParams] = useSearchParams();
  const status = searchParams.get('status') || 'pending';
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    measurementsV2Api.list({ status, page_size: 20 })
      .then((res) => setItems(res.items || res || []))
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [status]);

  return (
    <V2Layout>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Measurements</h1>
      <div className="flex gap-2 mb-4">
        <Link to="/v2/measurements?status=pending" className={`px-4 py-2 rounded-xl ${status === 'pending' ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}`}>
          Pending
        </Link>
        <Link to="/v2/measurements?status=assigned" className={`px-4 py-2 rounded-xl ${status === 'assigned' ? 'bg-blue-600 text-white' : 'bg-slate-200 text-slate-600'}`}>
          Assigned
        </Link>
      </div>
      {loading ? (
        <div className="animate-pulse h-48 bg-slate-200 rounded-xl" />
      ) : items.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500">
          No measurements
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((m) => (
            <Link key={m.id} to={`/v2/report/${m.id}`} className="block p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-300">
              <span className="font-mono text-sm">{m.id?.slice(0, 8)}...</span>
              <span className="text-slate-500 text-sm ml-2">{m.created_at ? new Date(m.created_at).toLocaleString() : ''}</span>
            </Link>
          ))}
        </div>
      )}
    </V2Layout>
  );
};

export default V2Measurements;
