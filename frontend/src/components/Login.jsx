import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../services/api';

const Login = () => {
  const [step, setStep] = useState('email'); // 'email' or 'pin'
  const [email, setEmail] = useState('');
  const [pinCode, setPinCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const { verifyPin, requestPin } = useAuth();
  const navigate = useNavigate();

  const handleEmailSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await requestPin(email);
      setMessage(response.message || 'PIN code sent to your email!');
      setStep('pin');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send PIN code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handlePinSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setMessage('');

    try {
      await verifyPin(email, pinCode);
      navigate('/dashboard');
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid PIN code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background-light dark:bg-background-dark flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8 bg-white dark:bg-slate-800 p-8 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-xl">
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-16 h-14 bg-primary/10 dark:bg-accent-blue/20 rounded-2xl mb-4">
            <span className="material-icons-round text-3xl text-primary dark:text-accent-blue">health_and_safety</span>
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            {step === 'email' ? 'Connexion' : 'Code PIN'}
          </h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {step === 'email' ? (
              <>
                Ou{' '}
                <Link to="/register" className="font-bold text-primary dark:text-accent-blue hover:opacity-80 transition-opacity">
                  créer un nouveau compte
                </Link>
                {' · '}
                <Link to="/v2" className="font-bold text-primary dark:text-accent-blue hover:opacity-80 transition-opacity">
                  Health Dashboard V2
                </Link>
              </>
            ) : (
              'Consultez vos e-mails pour le code PIN'
            )}
          </p>
        </div>

        {error && (
          <div className="bg-rose-50 dark:bg-rose-900/20 border border-rose-100 dark:border-rose-800/30 text-rose-700 dark:text-rose-400 px-4 py-3 rounded-2xl text-sm font-medium">
            {error}
          </div>
        )}

        {message && (
          <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-100 dark:border-emerald-800/30 text-emerald-700 dark:text-emerald-400 px-4 py-3 rounded-2xl text-sm font-medium">
            {message}
          </div>
        )}

        {step === 'email' ? (
          <form className="space-y-6" onSubmit={handleEmailSubmit}>
            <div className="space-y-1">
              <label htmlFor="email" className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 ml-1">
                Adresse e-mail
              </label>
              <div className="relative flex items-center">
                <span className="material-icons-round absolute left-3 text-slate-400">email</span>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all dark:text-white text-sm"
                  placeholder="votre@email.com"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold shadow-lg shadow-primary/20 active:scale-[0.98] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  <span>Envoyer le code PIN</span>
                  <span className="material-icons-round text-sm">arrow_forward</span>
                </>
              )}
            </button>
          </form>
        ) : (
          <form className="space-y-6" onSubmit={handlePinSubmit}>
            <div className="space-y-1 text-center">
              <label htmlFor="pin" className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">
                Code PIN
              </label>
              <input
                id="pin"
                name="pin"
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                maxLength="6"
                required
                value={pinCode}
                onChange={(e) => setPinCode(e.target.value.replace(/\D/g, ''))}
                className="w-full py-4 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all dark:text-white text-center text-3xl font-black tracking-[0.5em] placeholder:text-slate-200 dark:placeholder:text-slate-800"
                placeholder="000000"
              />
              <p className="text-[10px] text-slate-400 mt-2">
                Expire dans 10 minutes
              </p>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setStep('email');
                  setPinCode('');
                  setError('');
                  setMessage('');
                }}
                className="flex-1 py-4 bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-2xl font-bold active:scale-[0.98] transition-all"
              >
                Retour
              </button>
              <button
                type="submit"
                disabled={loading || pinCode.length !== 6}
                className="flex-[2] py-4 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold shadow-lg shadow-primary/20 active:scale-[0.98] transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                ) : (
                  <>
                    <span>Vérifier</span>
                    <span className="material-icons-round text-sm">check_circle</span>
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};

export default Login;


