import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { authApi } from '../../services/api';

const V2Login = () => {
  const [step, setStep] = useState('email');
  const [email, setEmail] = useState('');
  const [pinCode, setPinCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const { verifyPin, requestPin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/v2';

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');
    try {
      const response = await requestPin(email);
      setMessage(response.message || 'PIN sent to your email');
      setStep('pin');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send PIN');
    } finally {
      setLoading(false);
    }
  };

  const handlePinSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await verifyPin(email, pinCode);
      const userData = await authApi.getCurrentUser(localStorage.getItem('auth_token'));
      const role = userData?.role;
      if (role === 'admin') navigate('/v2/admin/organizations', { replace: true });
      else if (role === 'customer') navigate('/v2/dashboard', { replace: true });
      else if (role === 'retail') navigate('/v2/retail/history', { replace: true });
      else navigate(from || '/v2/dashboard', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid PIN');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-800">Health Dashboard V2</h1>
          <p className="text-slate-500 mt-1">
            {step === 'email' ? 'Sign in with your email' : 'Enter the PIN from your email'}
          </p>
        </div>
        {error && (
          <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-xl text-sm">{error}</div>
        )}
        {message && (
          <div className="mb-4 p-3 bg-green-50 text-green-700 rounded-xl text-sm">{message}</div>
        )}
        {step === 'email' ? (
          <form onSubmit={handleEmailSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-blue-500"
                placeholder="you@example.com"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-blue-600 text-white font-medium rounded-xl hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? 'Sending...' : 'Send PIN'}
            </button>
          </form>
        ) : (
          <form onSubmit={handlePinSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">PIN Code</label>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={pinCode}
                onChange={(e) => setPinCode(e.target.value.replace(/\D/g, ''))}
                className="w-full px-4 py-3 border border-slate-300 rounded-xl text-center text-2xl tracking-widest"
                placeholder="000000"
                required
              />
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => { setStep('email'); setPinCode(''); setError(''); }}
                className="flex-1 py-3 border border-slate-300 rounded-xl font-medium"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading || pinCode.length !== 6}
                className="flex-1 py-3 bg-blue-600 text-white font-medium rounded-xl disabled:opacity-50"
              >
                {loading ? 'Verifying...' : 'Verify'}
              </button>
            </div>
          </form>
        )}
        <p className="mt-6 text-center text-sm text-slate-500">
          <Link to="/v2/register" className="text-blue-600 hover:underline">Register with invite</Link>
          {' · '}
          <Link to="/" className="text-slate-500 hover:underline">Back to V1</Link>
        </p>
      </div>
    </div>
  );
};

export default V2Login;
