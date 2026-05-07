import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import autoAnimate from '@formkit/auto-animate';
import { healthDataApi, deviceApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { extractHealthMetrics, getBMICategory } from './DynamicField';

const Dashboard = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { user, logout } = useAuth();
  const [measurements, setMeasurements] = useState([]);
  const [stats, setStats] = useState({ total_measurements: 0, bmi_normal: 0, bmi_overweight: 0, bmi_obesity: 0 });
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [deviceFilter, setDeviceFilter] = useState(searchParams.get('device_id') || '');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [myMachines, setMyMachines] = useState([]);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    const fromUrl = searchParams.get('device_id') || '';
    if (fromUrl !== deviceFilter) setDeviceFilter(fromUrl);
  }, [searchParams]);

  useEffect(() => {
    listRef.current && autoAnimate(listRef.current);
  }, [listRef]);

  useEffect(() => {
    loadData();
  }, [page, searchTerm, deviceFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [measurementsData, statsData, machinesData] = await Promise.all([
        healthDataApi.getMeasurements(page, 20, searchTerm || null, deviceFilter || null),
        healthDataApi.getStats(),
        deviceApi.getMyMachinesStatus().catch(() => []),
      ]);
      setMeasurements(measurementsData.items);
      setTotal(measurementsData.total);
      setStats(statsData);
      setMyMachines(Array.isArray(machinesData) ? machinesData : []);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const day = date.getDate();
    const month = date.toLocaleString('fr-FR', { month: 'short' });
    const hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${day} ${month}, ${hours}:${minutes}`;
  };

  const handleMeasurementClick = (id) => {
    navigate(`/report/${id}`);
  };

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen pb-24">
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 ios-blur border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-primary/10 dark:bg-accent-blue/20 rounded-xl flex items-center justify-center">
            <span className="material-icons-round text-primary dark:text-accent-blue">health_and_safety</span>
          </div>
          <h1 className="text-lg font-black tracking-tight text-primary dark:text-white">HealthData</h1>
        </div>
        
        <div className="relative">
          <button 
            onClick={() => setShowUserMenu(!showUserMenu)}
            className="p-2 bg-slate-100 dark:bg-slate-800 rounded-full hover:scale-105 transition-transform"
          >
            <span className="material-icons-round text-slate-600 dark:text-slate-300 text-2xl">account_circle</span>
          </button>
          
          {showUserMenu && (
            <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-slate-800 rounded-2xl shadow-xl border border-slate-100 dark:border-slate-700 py-2 animate-fade-in z-[60]">
              <div className="px-4 py-2 border-b border-slate-50 dark:border-slate-700 mb-1">
                <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Connecté en tant que</p>
                <p className="text-sm font-bold text-slate-900 dark:text-white truncate">{user?.email}</p>
                <p className="text-[10px] font-black text-primary dark:text-accent-blue uppercase mt-0.5">{user?.role}</p>
              </div>
              <button 
                onClick={() => { logout(); navigate('/login'); }}
                className="w-full text-left px-4 py-2 text-sm font-bold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors flex items-center gap-2"
              >
                <span className="material-icons-round text-sm">logout</span>
                Déconnexion
              </button>

              {user?.role === 'admin' && (
                <div className="mt-2 pt-2 border-t border-slate-50 dark:border-slate-700">
                  <p className="px-4 py-1 text-[8px] font-black uppercase text-slate-400 tracking-[0.2em]">Outils Admin</p>
                  <button 
                    onClick={() => { setShowUserMenu(false); navigate('/users'); }}
                    className="w-full text-left px-4 py-2 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2"
                  >
                    <span className="material-icons-round text-sm text-primary">people</span>
                    Gérer les utilisateurs
                  </button>
                  <button 
                    onClick={() => { setShowUserMenu(false); navigate('/devices'); }}
                    className="w-full text-left px-4 py-2 text-sm font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors flex items-center gap-2"
                  >
                    <span className="material-icons-round text-sm text-primary">settings_remote</span>
                    Gérer les Appareils
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </nav>

      <main className="p-4 space-y-6 max-w-md mx-auto">
        {deviceFilter && (
          <div className="flex items-center justify-between gap-2 p-3 bg-primary/5 dark:bg-accent-blue/5 border border-primary/10 dark:border-accent-blue/10 rounded-2xl">
            <p className="text-xs font-bold text-slate-600 dark:text-slate-300">
              Appareil: <span className="text-primary dark:text-accent-blue">{deviceFilter}</span>
            </p>
            <button
              type="button"
              onClick={() => { setDeviceFilter(''); setSearchParams({}); }}
              className="text-[10px] font-bold uppercase text-slate-500 hover:text-primary dark:hover:text-accent-blue"
            >
              Voir tout
            </button>
          </div>
        )}

        {myMachines.length > 0 && (
          <div className="space-y-2">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500 px-1">
              Mes machines — activité
            </h3>
            <div className="flex gap-3 overflow-x-auto hide-scrollbar pb-1 snap-x">
              {myMachines.map((m) => (
                <button
                  key={m.device_id}
                  type="button"
                  onClick={() => {
                    setDeviceFilter(m.device_id);
                    setSearchParams({ device_id: m.device_id });
                    setPage(1);
                  }}
                  className="snap-start shrink-0 w-[min(260px,85vw)] text-left p-4 rounded-3xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 shadow-sm hover:border-primary/40 dark:hover:border-accent-blue/40 transition-colors"
                >
                  <p className="font-black text-sm text-slate-900 dark:text-white truncate">{m.name}</p>
                  <p className="text-[10px] text-slate-400 font-mono truncate mt-0.5">{m.device_id}</p>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-[10px]">
                    <div>
                      <span className="text-slate-400 uppercase tracking-wider">24h</span>
                      <p className="font-bold text-primary dark:text-accent-blue">{m.count_24h}</p>
                    </div>
                    <div>
                      <span className="text-slate-400 uppercase tracking-wider">7 j.</span>
                      <p className="font-bold text-slate-700 dark:text-slate-200">{m.count_7d}</p>
                    </div>
                  </div>
                  <p className="text-[9px] text-slate-500 mt-2">
                    Dernier rapport :{' '}
                    {m.last_measurement_at
                      ? formatDate(m.last_measurement_at)
                      : '—'}
                  </p>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-emerald-50 dark:bg-emerald-900/20 p-4 rounded-3xl border border-emerald-100 dark:border-emerald-800/30 flex flex-col items-center">
            <span className="text-[8px] font-black text-emerald-700 dark:text-emerald-400 uppercase tracking-widest mb-1 text-center">Normal</span>
            <p className="text-2xl font-black text-emerald-800 dark:text-emerald-300">{stats.bmi_normal}</p>
          </div>
          <div className="bg-amber-50 dark:bg-amber-900/20 p-4 rounded-3xl border border-amber-100 dark:border-amber-800/30 flex flex-col items-center">
            <span className="text-[8px] font-black text-amber-700 dark:text-amber-400 uppercase tracking-widest mb-1 text-center">Surpoids</span>
            <p className="text-2xl font-black text-amber-800 dark:text-amber-300">{stats.bmi_overweight}</p>
          </div>
          <div className="bg-rose-50 dark:bg-rose-900/20 p-4 rounded-3xl border border-rose-100 dark:border-rose-800/30 flex flex-col items-center">
            <span className="text-[8px] font-black text-rose-700 dark:text-rose-400 uppercase tracking-widest mb-1 text-center">Obésité</span>
            <p className="text-2xl font-black text-rose-800 dark:text-rose-300">{stats.bmi_obesity}</p>
          </div>
        </div>

        {/* Search and Filters */}
        <div className="space-y-3">
          <div className="relative flex items-center">
            <span className="material-icons-round absolute left-4 text-slate-400">search</span>
            <input
              className="w-full pl-12 pr-4 py-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-3xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all shadow-sm font-medium text-sm"
              placeholder="Rechercher par ID Patient..."
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
            />
          </div>
          
          <div className="flex gap-2 overflow-x-auto hide-scrollbar pb-1">
            <button 
              onClick={() => navigate('/devices')}
              className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-xs font-bold shadow-sm whitespace-nowrap active:scale-95 transition-all"
            >
              <span className="material-icons-round text-sm text-primary">devices</span>
              Mes Appareils
            </button>
            <button 
              onClick={() => navigate('/customers')}
              className="flex items-center gap-2 px-5 py-3 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-2xl text-xs font-bold shadow-sm whitespace-nowrap active:scale-95 transition-all"
            >
              <span className="material-icons-round text-sm text-accent-blue">people</span>
              Mes Patients
            </button>
          </div>
        </div>

        {/* Measurements List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-400 dark:text-slate-500">Derniers Rapports</h3>
            <span className="text-[10px] font-bold text-slate-400">{total} au total</span>
          </div>

          <div className="grid grid-cols-1 gap-3" ref={listRef}>
            {loading ? (
              <div className="text-center py-10 text-slate-500 font-medium italic">Chargement des données...</div>
            ) : measurements.length === 0 ? (
              <div className="bg-white dark:bg-slate-800 p-10 rounded-3xl border border-dashed border-slate-200 dark:border-slate-700 text-center">
                <span className="material-icons-round text-4xl text-slate-200 dark:text-slate-700 mb-2">find_in_page</span>
                <p className="text-slate-400 text-sm font-medium">Aucun rapport trouvé</p>
              </div>
            ) : (
              measurements.map((measurement) => {
                const metrics = extractHealthMetrics(measurement.measurement_data);
                const bmiInfo = getBMICategory(metrics.bmi);
                const colorClasses = {
                  normal: 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400',
                  overweight: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400',
                  obesity: 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-400',
                  underweight: 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400',
                };
                const bmiColorClass = colorClasses[bmiInfo.category] || 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300';

                return (
                  <div
                    key={measurement.id}
                    onClick={() => handleMeasurementClick(measurement.id)}
                    className="bg-white dark:bg-slate-800 p-5 rounded-[2rem] border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-4 active:scale-[0.98] transition-all cursor-pointer group"
                  >
                    <div className={`h-14 w-14 rounded-2xl flex items-center justify-center font-black text-xl transition-colors ${bmiColorClass}`}>
                      {metrics.bmi || '--'}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="font-black text-slate-900 dark:text-white truncate">
                          {measurement.customer?.full_name || measurement.patient_id || 'Patient Inconnu'}
                        </h4>
                        {measurement.device_id && (
                          <span className="px-2 py-0.5 bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-700 rounded-full text-[8px] font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest">
                            {measurement.device_id}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] font-bold text-slate-400">{formatDate(measurement.created_at)}</span>
                        <span className="w-1 h-1 bg-slate-200 dark:bg-slate-700 rounded-full"></span>
                        <span className="text-[10px] font-black uppercase tracking-widest text-primary dark:text-accent-blue opacity-70">
                          {metrics.weight || '--'}kg / {metrics.height || '--'}cm
                        </span>
                      </div>
                    </div>
                    
                    <span className="material-icons-round text-slate-300 dark:text-slate-600 group-hover:translate-x-1 transition-transform">chevron_right</span>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {total > page * 20 && (
          <button
            onClick={() => setPage(page + 1)}
            className="w-full py-4 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-3xl text-xs font-black text-slate-500 dark:text-slate-400 uppercase tracking-widest shadow-sm active:scale-[0.98] transition-all"
          >
            Charger plus de rapports
          </button>
        )}
      </main>

      <div className="fixed bottom-24 right-6 z-40">
        <button
          onClick={() => navigate('/add')}
          className="w-16 h-16 bg-primary dark:bg-accent-blue text-white rounded-[2rem] shadow-xl shadow-primary/30 flex items-center justify-center active:scale-90 transition-transform"
        >
          <span className="material-icons-round text-3xl">add</span>
        </button>
      </div>

      <footer className="fixed bottom-0 w-full bg-white/90 dark:bg-slate-900/90 ios-blur border-t border-slate-200 dark:border-slate-800 px-6 py-2 pb-6 flex justify-between items-center z-50">
        <button onClick={() => navigate('/dashboard')} className="flex flex-col items-center gap-1 text-primary dark:text-accent-blue">
          <span className="material-icons-round">dashboard</span>
          <span className="text-[10px] font-bold">Accueil</span>
        </button>
        <button onClick={() => navigate('/dashboard')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">description</span>
          <span className="text-[10px] font-medium">Rapports</span>
        </button>
        <button onClick={() => navigate('/customers')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">groups</span>
          <span className="text-[10px] font-medium">Patients</span>
        </button>
        <button onClick={() => navigate('/devices')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">settings_remote</span>
          <span className="text-[10px] font-medium">Appareils</span>
        </button>
      </footer>
    </div>
  );
};

export default Dashboard;
