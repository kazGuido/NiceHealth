import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import V2Layout from '../V2Layout';
import { retailApi } from '../../../services/apiV2';
import { useAuth } from '../../../contexts/AuthContext';

const V2RetailSettings = () => {
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleDeleteData = async () => {
    if (confirm !== 'DELETE') return;
    setLoading(true);
    try {
      await retailApi.deleteMyData();
      setMessage('Your data has been deleted.');
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to delete data');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (confirm !== 'DELETE') return;
    setLoading(true);
    try {
      await retailApi.deleteMe();
      logout();
      navigate('/v2/login');
    } catch (err) {
      setMessage(err.response?.data?.detail || 'Failed to delete account');
    } finally {
      setLoading(false);
    }
  };

  return (
    <V2Layout>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Settings</h1>
      <div className="space-y-6 max-w-md">
        <div className="bg-white p-6 rounded-xl border border-slate-200">
          <h2 className="font-semibold text-slate-800 mb-2">Delete my data</h2>
          <p className="text-sm text-slate-500 mb-4">Permanently remove all your measurement data.</p>
          <input
            type="text"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder="Type DELETE to confirm"
            className="w-full px-4 py-2 border rounded-lg mb-2"
          />
          <button onClick={handleDeleteData} disabled={confirm !== 'DELETE' || loading} className="px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50">
            Delete Data
          </button>
        </div>
        <div className="bg-white p-6 rounded-xl border border-slate-200">
          <h2 className="font-semibold text-slate-800 mb-2">Delete account</h2>
          <p className="text-sm text-slate-500 mb-4">Permanently delete your account.</p>
          <button onClick={handleDeleteAccount} disabled={confirm !== 'DELETE' || loading} className="px-4 py-2 bg-red-600 text-white rounded-lg disabled:opacity-50">
            Delete Account
          </button>
        </div>
        {message && <p className="text-sm text-slate-600">{message}</p>}
      </div>
    </V2Layout>
  );
};

export default V2RetailSettings;
