import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { healthDataApi, customerApi, deviceApi } from '../services/api';

const MeasurementForm = () => {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [devices, setDevices] = useState([]);
  const [formData, setFormData] = useState({
    patient_id: '',
    device_id: '',
    customer_id: '',
    measurement_data: {
      height: '',
      weight: '',
      blood_pressure: '',
      heart_rate: '',
    }
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [customersData, devicesData] = await Promise.all([
        customerApi.getCustomers(),
        deviceApi.getDevices()
      ]);
      setCustomers(customersData);
      setDevices(devicesData);
      
      // Auto-select first device if available
      if (devicesData.length > 0) {
        setFormData(prev => ({ ...prev, device_id: devicesData[0].device_id }));
      }
    } catch (error) {
      console.error('Error loading initial data:', error);
    }
  };

  const handleChange = (field, value) => {
    if (field === 'patient_id' || field === 'device_id' || field === 'customer_id') {
      setFormData(prev => ({ ...prev, [field]: value }));
    } else {
      setFormData(prev => ({
        ...prev,
        measurement_data: {
          ...prev.measurement_data,
          [field]: value
        }
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const cleanedData = {
        patient_id: formData.patient_id || null,
        device_id: formData.device_id || null,
        customer_id: formData.customer_id || null,
        measurement_data: {}
      };

      Object.entries(formData.measurement_data).forEach(([key, value]) => {
        if (value !== '') {
          cleanedData.measurement_data[key] = isNaN(value) ? value : parseFloat(value);
        }
      });

      await healthDataApi.createMeasurement(cleanedData);
      navigate('/dashboard');
    } catch (error) {
      console.error('Error creating measurement:', error);
      alert('Erreur lors de la création du rapport');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen pb-10">
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 ios-blur border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/dashboard')}
            className="p-2 -ml-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
          >
            <span className="material-icons-round text-primary dark:text-accent-blue">arrow_back_ios_new</span>
          </button>
          <h1 className="text-lg font-bold tracking-tight text-primary dark:text-white">Nouveau Rapport</h1>
        </div>
      </nav>

      <main className="p-4 max-w-md mx-auto space-y-6">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-icons-round text-primary dark:text-accent-blue text-lg">person_search</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Informations Patient</h3>
            </div>
            
            <div className="space-y-1">
              <label className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 ml-1">Associer à un Patient (Optionnel)</label>
              <select
                value={formData.customer_id}
                onChange={(e) => handleChange('customer_id', e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all text-sm"
              >
                <option value="">Aucun patient spécifique</option>
                {customers.map(c => (
                  <option key={c.id} value={c.id}>{c.full_name}</option>
                ))}
              </select>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 ml-1">ID Patient (ID externe)</label>
              <input
                type="text"
                value={formData.patient_id}
                onChange={(e) => handleChange('patient_id', e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all text-sm"
                placeholder="Ex: NDT-98241"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 ml-1">Appareil Source</label>
              <select
                required
                value={formData.device_id}
                onChange={(e) => handleChange('device_id', e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all text-sm"
              >
                <option value="">Sélectionner un appareil</option>
                {devices.map(d => (
                  <option key={d.id} value={d.device_id}>{d.name || d.device_id}</option>
                ))}
              </select>
              {devices.length === 0 && (
                <p className="text-[8px] text-rose-500 font-bold ml-1 uppercase mt-1">Aucun appareil disponible</p>
              )}
            </div>
          </div>

          <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-5">
            <div className="flex items-center gap-2 mb-2">
              <span className="material-icons-round text-primary dark:text-accent-blue text-lg">straighten</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Mesures de Santé</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 ml-1">Taille (cm)</label>
                <input
                  type="number"
                  value={formData.measurement_data.height}
                  onChange={(e) => handleChange('height', e.target.value)}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all text-sm"
                  placeholder="178"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 ml-1">Poids (kg)</label>
                <input
                  type="number"
                  step="0.1"
                  value={formData.measurement_data.weight}
                  onChange={(e) => handleChange('weight', e.target.value)}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all text-sm"
                  placeholder="76.5"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 ml-1">Pression Artérielle</label>
              <input
                type="text"
                value={formData.measurement_data.blood_pressure}
                onChange={(e) => handleChange('blood_pressure', e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all text-sm"
                placeholder="122/81"
              />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 ml-1">Fréq. Cardiaque (bpm)</label>
              <input
                type="number"
                value={formData.measurement_data.heart_rate}
                onChange={(e) => handleChange('heart_rate', e.target.value)}
                className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue focus:border-transparent outline-none transition-all text-sm"
                placeholder="72"
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
                <span>Enregistrer le Rapport</span>
                <span className="material-icons-round text-sm">save</span>
              </>
            )}
          </button>
        </form>
      </main>
    </div>
  );
};

export default MeasurementForm;
