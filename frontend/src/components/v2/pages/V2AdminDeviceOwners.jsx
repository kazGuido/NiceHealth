import React from 'react';
import V2Layout from '../V2Layout';

const V2AdminDeviceOwners = () => (
  <V2Layout>
    <h1 className="text-2xl font-bold text-slate-800 mb-6">Device Owners</h1>
    <div className="bg-white p-6 rounded-xl border border-slate-200">
      <p className="text-slate-500">Assign devices to organizations. Use deviceOwnersApi.add / list / remove.</p>
    </div>
  </V2Layout>
);

export default V2AdminDeviceOwners;
