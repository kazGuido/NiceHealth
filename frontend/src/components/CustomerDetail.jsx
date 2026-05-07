import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import autoAnimate from '@formkit/auto-animate';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { customerApi, healthDataApi, getFileUrl } from '../services/api';
import { extractHealthMetrics, getBMICategory } from './DynamicField';

const CustomerDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [customer, setCustomer] = useState(null);
  const [measurements, setMeasurements] = useState([]);
  const [loading, setLoading] = useState(true);
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current && autoAnimate(listRef.current);
  }, [listRef]);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [customerData, measurementsData] = await Promise.all([
        customerApi.getCustomer(id),
        healthDataApi.getMeasurements(1, 50, null, null, id)
      ]);
      setCustomer(customerData);
      setMeasurements(measurementsData.items.reverse()); // Chronological order for charts
    } catch (error) {
      console.error('Error loading customer data:', error);
    } finally {
      setLoading(false);
    }
  };

  const chartData = measurements.map(m => {
    const metrics = extractHealthMetrics(m.measurement_data);
    const date = new Date(m.created_at);
    return {
      name: date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short' }),
      bmi: metrics.bmi,
      weight: metrics.weight,
      height: metrics.height,
      timestamp: m.created_at
    };
  }).filter(d => d.bmi || d.weight);

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      day: 'numeric',
      month: 'long',
      year: 'numeric'
    });
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-500 font-bold uppercase tracking-widest animate-pulse">Chargement...</div>;
  if (!customer) return <div className="min-h-screen flex items-center justify-center text-slate-500 font-bold">Client non trouvé</div>;

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen pb-24">
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 ios-blur border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/customers')} className="p-2 -ml-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors">
            <span className="material-icons-round text-primary dark:text-accent-blue">arrow_back_ios_new</span>
          </button>
          <h1 className="text-lg font-bold tracking-tight text-primary dark:text-white">Profil Patient</h1>
        </div>
      </nav>

      <main className="p-4 max-w-md mx-auto space-y-6">
        {/* Header Profile */}
        <div className="bg-white dark:bg-slate-800 rounded-[2.5rem] p-8 shadow-xl border border-slate-100 dark:border-slate-700 flex flex-col items-center text-center space-y-4">
          <div className="relative">
            <div className="h-24 w-24 rounded-3xl bg-primary/5 overflow-hidden flex items-center justify-center border-4 border-white dark:border-slate-700 shadow-lg">
              {customer.photo_url ? (
                <img src={getFileUrl(customer.photo_url)} alt={customer.full_name} className="h-full w-full object-cover" />
              ) : (
                <span className="material-icons-round text-5xl text-primary/20">person</span>
              )}
            </div>
            <div className="absolute -bottom-2 -right-2 bg-emerald-500 h-6 w-6 rounded-full border-4 border-white dark:border-slate-800 shadow-sm"></div>
          </div>
          
          <div>
            <h2 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">{customer.full_name}</h2>
            <p className="text-[10px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-[0.2em] mt-1">Patient ID: {customer.id.slice(0, 8)}</p>
          </div>

          <div className="flex gap-2 w-full pt-2">
            <div className="flex-1 bg-slate-50 dark:bg-slate-900/50 p-3 rounded-2xl border border-slate-100 dark:border-slate-700">
              <p className="text-[8px] font-black text-slate-400 uppercase mb-1">Dernière Mesure</p>
              <p className="text-xs font-bold text-slate-700 dark:text-slate-300">
                {measurements.length > 0 ? formatDate(measurements[measurements.length-1].created_at) : 'Aucune'}
              </p>
            </div>
          </div>
        </div>

        {/* Charts Section */}
        {chartData.length > 1 ? (
          <div className="space-y-6">
            <div className="flex items-center gap-2 px-1">
              <span className="material-icons-round text-primary dark:text-accent-blue text-lg">insights</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Évolution de Santé</h3>
            </div>

            {/* BMI Chart */}
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex justify-between items-center mb-6">
                <h4 className="text-sm font-black text-slate-900 dark:text-white">Indice de Masse Corporelle</h4>
                <span className="px-3 py-1 bg-primary/5 dark:bg-accent-blue/10 text-primary dark:text-accent-blue rounded-full text-[10px] font-black uppercase tracking-widest">Tendance</span>
              </div>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="colorBmi" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#2563eb" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#2563eb" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 700, fill: '#94a3b8'}} />
                    <YAxis hide domain={['dataMin - 2', 'dataMax + 2']} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', fontWeight: 700, fontSize: '12px' }}
                    />
                    <Area type="monotone" dataKey="bmi" stroke="#2563eb" strokeWidth={4} fillOpacity={1} fill="url(#colorBmi)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Weight Chart */}
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="flex justify-between items-center mb-6">
                <h4 className="text-sm font-black text-slate-900 dark:text-white">Poids (kg)</h4>
                <span className="px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] font-black uppercase tracking-widest">Suivi</span>
              </div>
              <div className="h-48 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 700, fill: '#94a3b8'}} />
                    <YAxis hide domain={['dataMin - 5', 'dataMax + 5']} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '16px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)', fontWeight: 700, fontSize: '12px' }}
                    />
                    <Line type="monotone" dataKey="weight" stroke="#10b981" strokeWidth={4} dot={{ r: 6, fill: '#10b981', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 8 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-slate-800 p-10 rounded-3xl border border-dashed border-slate-200 dark:border-slate-700 text-center">
            <span className="material-icons-round text-4xl text-slate-200 dark:text-slate-700 mb-2">monitoring</span>
            <p className="text-slate-400 text-sm font-medium">Plus de mesures nécessaires pour afficher les graphiques</p>
          </div>
        )}

        {/* Measurements List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500">Historique complet</h3>
          </div>
          <div className="space-y-2" ref={listRef}>
            {[...measurements].reverse().map(m => {
              const metrics = extractHealthMetrics(m.measurement_data);
              return (
                <div key={m.id} onClick={() => navigate(`/report/${m.id}`)} className="bg-white dark:bg-slate-800 p-4 rounded-2xl border border-slate-100 dark:border-slate-700 shadow-sm flex items-center justify-between active:scale-95 transition-transform cursor-pointer">
                  <div>
                    <p className="text-xs font-black text-slate-900 dark:text-white">{formatDate(m.created_at)}</p>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{m.device_id || 'KIOSK'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-black text-primary dark:text-accent-blue">{metrics.bmi || '--'} IMC</p>
                    <p className="text-[10px] font-bold text-slate-400">{metrics.weight || '--'} kg</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </main>

      <footer className="fixed bottom-0 w-full bg-white/90 dark:bg-slate-900/90 ios-blur border-t border-slate-200 dark:border-slate-800 px-6 py-2 pb-6 flex justify-between items-center z-50">
        <button onClick={() => navigate('/dashboard')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">dashboard</span>
          <span className="text-[10px] font-medium">Accueil</span>
        </button>
        <button onClick={() => navigate('/dashboard')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">description</span>
          <span className="text-[10px] font-medium">Rapports</span>
        </button>
        <button onClick={() => navigate('/customers')} className="flex flex-col items-center gap-1 text-primary dark:text-accent-blue">
          <span className="material-icons-round">groups</span>
          <span className="text-[10px] font-bold">Patients</span>
        </button>
        <button onClick={() => navigate('/devices')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">settings_remote</span>
          <span className="text-[10px] font-medium">Appareils</span>
        </button>
      </footer>
    </div>
  );
};

export default CustomerDetail;

