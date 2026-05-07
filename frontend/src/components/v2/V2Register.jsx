import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { authRetailApi } from '../../services/apiV2';

const V2Register = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [step, setStep] = useState('request');
  const [pinCode, setPinCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) setError('Invalid or missing invite token');
  }, [token]);

  const handleRequestPin = async (e) => {
    e.preventDefault();
    if (!token) return;
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const res = await authRetailApi.requestPin(token);
      setMessage(res.message || 'PIN sent to your email');
      setStep('verify');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send PIN');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!token) return;
    setLoading(true);
    setError('');
    try {
      const res = await authRetailApi.register(token, pinCode);
      if (res.access_token) {
        localStorage.setItem('auth_token', res.access_token);
        window.location.href = '/v2/retail/history';
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8 text-center">
          <h1 className="text-xl font-bold text-slate-800">Invalid Invite</h1>
          <p className="text-slate-500 mt-2">This registration link is invalid or expired.</p>
          <Link to="/v2/login" className="mt-4 inline-block text-blue-600 hover:underline">Go to Login</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-xl font-bold text-slate-800 text-center">Complete Registration</h1>
        <p className="text-slate-500 text-center mt-1">You were invited to access your health reports</p>
        {error && <div className="mt-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{error}</div>}
        {message && <div className="mt-4 p-3 bg-green-50 text-green-700 rounded-xl text-sm">{message}</div>}
        {step === 'request' ? (
          <form onSubmit={handleRequestPin} className="mt-6">
            <button type="submit" disabled={loading} className="w-full py-3 bg-blue-600 text-white font-medium rounded-xl">
              {loading ? 'Sending...' : 'Send PIN to my email'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="mt-6 space-y-4">
            <input
              type="text"
              inputMode="numeric"
              maxLength={6}
              value={pinCode}
              onChange={(e) => setPinCode(e.target.value.replace(/\D/g, ''))}
              className="w-full px-4 py-3 border rounded-xl text-center text-2xl"
              placeholder="Enter PIN"
              required
            />
            <button type="submit" disabled={loading || pinCode.length !== 6} className="w-full py-3 bg-blue-600 text-white font-medium rounded-xl">
              {loading ? 'Verifying...' : 'Complete Registration'}
            </button>
          </form>
        )}
        <p className="mt-6 text-center text-sm text-slate-500">
          <Link to="/v2/login" className="text-blue-600 hover:underline">Back to Login</Link>
        </p>
      </div>
    </div>
  );
};

export default V2Register;
