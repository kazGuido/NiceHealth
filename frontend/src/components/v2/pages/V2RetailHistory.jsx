import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import V2Layout from '../V2Layout';
import { retailApi } from '../../../services/apiV2';

const V2RetailHistory = () => {
  const [measurements, setMeasurements] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    retailApi.getMeasurements({ page_size: 50 })
      .then((res) => setMeasurements(res.items || res || []))
      .catch(() => setMeasurements([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <V2Layout>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">My Measurements</h1>
      {loading ? (
        <div className="animate-pulse h-48 bg-slate-200 rounded-xl" />
      ) : measurements.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500">
          No measurements yet. Get measured at a partner location to see your reports here.
        </div>
      ) : (
        <div className="space-y-2">
          {measurements.map((m) => (
            <Link key={m.id} to={`/v2/report/${m.id}`} className="block p-4 bg-white rounded-xl border border-slate-200 hover:border-blue-300">
              <span className="font-medium text-slate-800">Report</span>
              <span className="text-slate-500 text-sm ml-2">{m.created_at ? new Date(m.created_at).toLocaleDateString() : ''}</span>
            </Link>
          ))}
        </div>
      )}
    </V2Layout>
  );
};

export default V2RetailHistory;
