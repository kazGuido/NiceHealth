import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';
import { healthDataApi, customerApi, getFileUrl } from '../services/api';
import { extractHealthMetrics, getBMICategory, getBMIGaugePosition, getBMITypeLabel, getStatusLabel } from './DynamicField';

const ReportDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [measurement, setMeasurement] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [loadingCustomers, setLoadingCustomers] = useState(false);
  const [attributing, setAttributing] = useState(false);
  const [attributeCustomerId, setAttributeCustomerId] = useState('');
  const [sendToEmail, setSendToEmail] = useState('');
  const [sendingToEmail, setSendingToEmail] = useState(false);
  const lastAutoAnalyzeId = useRef(null);

  useEffect(() => {
    loadMeasurement();
  }, [id]);

  useEffect(() => {
    if (measurement) {
      customerApi.getCustomers(0, 200).then((list) => setCustomers(list)).catch(() => {});
    }
  }, [measurement]);

  // Lancer l'analyse IA dès que le rapport est chargé (une requête, affichage du résultat)
  useEffect(() => {
    if (!measurement || !id) return;
    if (lastAutoAnalyzeId.current === id) return;
    lastAutoAnalyzeId.current = id;
    handleAnalyze();
  }, [measurement, id]);

  const loadMeasurement = async () => {
    try {
      setLoading(true);
      const data = await healthDataApi.getMeasurement(id);
      setMeasurement(data);
    } catch (error) {
      console.error('Error loading measurement:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (loadingAnalysis) return;
    try {
      setLoadingAnalysis(true);
      const data = await healthDataApi.analyzeReport(id);
      setAnalysis(data);
    } catch (error) {
      console.error('Error analyzing report:', error);
      setAnalysis({ error: "Erreur lors de l'analyse IA." });
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const day = date.getDate();
    const month = date.toLocaleString('fr-FR', { month: 'long' });
    const hours = date.getHours();
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${day} ${month} ${date.getFullYear()} • ${hours}:${minutes}`;
  };

  const handlePrint = () => {
    window.print();
  };

  const handleEmail = async () => {
    if (sendingEmail) return;
    
    const targetEmail = measurement.customer?.email || measurement.customer?.user?.email;
    if (!targetEmail) {
      alert("Ce client n'a pas d'adresse e-mail configurée.");
      return;
    }

    try {
      setSendingEmail(true);
      await healthDataApi.sendReportEmail(id);
      alert(`Rapport envoyé avec succès à ${targetEmail}`);
    } catch (error) {
      console.error('Error sending email:', error);
      alert("Erreur lors de l'envoi de l'e-mail. Vérifiez la configuration SMTP.");
    } finally {
      setSendingEmail(false);
    }
  };

  const handleSendToEmail = async () => {
    const email = sendToEmail?.trim();
    if (!email) {
      alert('Entrez une adresse e-mail.');
      return;
    }
    try {
      setSendingToEmail(true);
      await healthDataApi.sendReportEmail(id, { email });
      alert(`Rapport envoyé à ${email}`);
      setSendToEmail('');
    } catch (e) {
      console.error(e);
      alert(e.response?.data?.detail || "Impossible d'envoyer l'e-mail.");
    } finally {
      setSendingToEmail(false);
    }
  };

  const handleAttribute = async (overrideCustomerId) => {
    if (attributing) return;
    const customerId = overrideCustomerId !== undefined ? overrideCustomerId : attributeCustomerId;
    try {
      setAttributing(true);
      const payload = customerId ? { customer_id: customerId } : { customer_id: null };
      const updated = await healthDataApi.attributeMeasurement(id, payload);
      setMeasurement(updated);
      setAttributeCustomerId('');
      alert(customerId ? 'Mesure attribuée au client.' : 'Attribution retirée.');
    } catch (e) {
      console.error(e);
      alert("Impossible d'attribuer la mesure.");
    } finally {
      setAttributing(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex items-center justify-center">
        <p className="text-slate-500 font-bold animate-pulse">CHARGEMENT...</p>
      </div>
    );
  }

  if (!measurement) {
    return (
      <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen flex items-center justify-center">
        <p className="text-slate-500 font-bold">RAPPORT NON TROUVÉ</p>
      </div>
    );
  }

  const metrics = extractHealthMetrics(measurement.measurement_data);
  const bmiInfo = getBMICategory(metrics.bmi);
  const bmiGaugePosition = getBMIGaugePosition(metrics.bmi);

  // Parse blood pressure
  let systolic = null;
  let diastolic = null;
  if (metrics.bloodPressure) {
    const bpMatch = String(metrics.bloodPressure).match(/(\d+)\s*[/-]\s*(\d+)/);
    if (bpMatch) {
      systolic = bpMatch[1];
      diastolic = bpMatch[2];
    }
  }

  // Check if we have body composition metrics
  const hasBodyComposition = metrics.fatRate || metrics.waterRate || metrics.muscleRate || metrics.boneMass || metrics.metabolism || metrics.visceralFat;

  return (
    <div className="bg-background-light dark:bg-background-dark text-slate-900 dark:text-slate-100 min-h-screen pb-24">
      <nav className="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 ios-blur border-b border-slate-200 dark:border-slate-800 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button 
            onClick={() => navigate('/dashboard')}
            className="p-2 -ml-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
          >
            <span className="material-icons-round text-primary dark:text-accent-blue">arrow_back_ios_new</span>
          </button>
          <h1 className="text-lg font-bold tracking-tight text-primary dark:text-white">Détails du Rapport</h1>
        </div>
        <button className="p-2 bg-primary/10 dark:bg-accent-blue/20 rounded-full">
          <span className="material-icons-round text-primary dark:text-accent-blue">share</span>
        </button>
      </nav>

      <main className="p-4 max-w-md mx-auto space-y-6">
        {/* Patient Profile / Mini Header */}
        {(measurement.customer || metrics.userInfo.name) && (
          <div 
            onClick={() => measurement.customer && navigate(`/customer/${measurement.customer.id}`)}
            className="bg-white dark:bg-slate-800 p-4 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-4 cursor-pointer"
          >
            <div className="h-12 w-12 rounded-2xl bg-primary/5 overflow-hidden flex items-center justify-center border border-slate-100 dark:border-slate-700 shadow-inner">
              {measurement.customer?.photo_url ? (
                <img src={getFileUrl(measurement.customer.photo_url)} alt={measurement.customer.full_name} className="h-full w-full object-cover" />
              ) : (
                <span className="material-icons-round text-2xl text-primary/30 dark:text-accent-blue/30">person</span>
              )}
            </div>
            <div className="flex-1">
              <p className="text-[8px] font-black uppercase text-slate-400 tracking-[0.2em]">Patient</p>
              <h3 className="font-bold text-slate-900 dark:text-white">
                {measurement.customer?.full_name || metrics.userInfo.name || 'Anonyme'}
              </h3>
              {(metrics.userInfo.age || metrics.userInfo.sex) && (
                <p className="text-[10px] text-slate-400 font-bold">
                  {metrics.userInfo.sex === '1' || metrics.userInfo.sex === 1 ? 'Homme' : metrics.userInfo.sex === '0' || metrics.userInfo.sex === 0 ? 'Femme' : ''} 
                  {metrics.userInfo.age ? ` • ${metrics.userInfo.age} ans` : ''}
                </p>
              )}
            </div>
            {measurement.customer && <span className="material-icons-round text-slate-300 dark:text-slate-600 text-sm">chevron_right</span>}
          </div>
        )}

        {/* Attribuer à un client */}
        <div className="bg-white dark:bg-slate-800 rounded-3xl p-4 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-2 mb-3">
            <span className="material-icons-round text-primary dark:text-accent-blue text-lg">person_add</span>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Attribution</h3>
          </div>
          {measurement.customer ? (
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <p className="text-sm text-slate-700 dark:text-slate-300">
                Attribué à: <strong>{measurement.customer.full_name}</strong>
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => handleAttribute(null)}
                  disabled={attributing}
                  className="text-[10px] font-bold uppercase text-slate-500 hover:text-rose-600 dark:hover:text-rose-400"
                >
                  Retirer
                </button>
                <span className="text-slate-300 dark:text-slate-600">|</span>
                <select
                  value={attributeCustomerId}
                  onChange={(e) => setAttributeCustomerId(e.target.value)}
                  className="text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1"
                >
                  <option value="">Changer de client…</option>
                  {(Array.isArray(customers) ? customers : (customers?.items || [])).map((c) => (
                    <option key={c.id} value={c.id}>{c.full_name}</option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={handleAttribute}
                  disabled={attributing || !attributeCustomerId}
                  className="text-[10px] font-black uppercase bg-primary dark:bg-accent-blue text-white px-3 py-1 rounded-lg disabled:opacity-50"
                >
                  {attributing ? '…' : 'Appliquer'}
                </button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-2 items-center">
              <select
                value={attributeCustomerId}
                onChange={(e) => setAttributeCustomerId(e.target.value)}
                className="text-sm bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-600 rounded-xl px-3 py-2 flex-1 min-w-[140px]"
              >
                <option value="">Sélectionner un client…</option>
                {(Array.isArray(customers) ? customers : (customers?.items || [])).map((c) => (
                  <option key={c.id} value={c.id}>{c.full_name}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={handleAttribute}
                disabled={attributing || !attributeCustomerId}
                className="text-xs font-black uppercase bg-primary dark:bg-accent-blue text-white px-4 py-2 rounded-xl disabled:opacity-50"
              >
                {attributing ? 'En cours…' : 'Attribuer'}
              </button>
            </div>
          )}
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <div className="flex flex-col">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-400 dark:text-slate-500">Référence</span>
              <h2 className="text-2xl font-black text-primary dark:text-white tracking-tight">
                {metrics.recordNo || measurement.patient_id || `#${measurement.id.slice(0, 8)}`}
              </h2>
            </div>
            <div className="text-right">
              <div className="inline-block px-3 py-1 bg-slate-100 dark:bg-slate-700 rounded-full text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
                {metrics.measureTime ? (metrics.measureTime.replace(/-/g, '/')) : formatDate(measurement.created_at)}
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-4 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-100 dark:border-slate-700">
            <div className="h-10 w-10 rounded-xl bg-primary/10 dark:bg-accent-blue/20 flex items-center justify-center text-primary dark:text-accent-blue">
              <span className="material-icons-round text-2xl">devices</span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Source Appareil</p>
              <p className="text-sm font-bold dark:text-slate-200 truncate">
                {measurement.device_id || measurement.kiosk_location || measurement.measurement_data?.deviceNo || measurement.measurement_data?.deviceModel || 'Source Inconnue'}
              </p>
              {(measurement.measurement_data?.deviceNo || measurement.measurement_data?.deviceModel) && (
                <p className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">
                  {[measurement.measurement_data?.deviceNo, measurement.measurement_data?.deviceModel].filter(Boolean).join(' • ')}
                </p>
              )}
            </div>
          </div>

          {(metrics.bmiNorm || metrics.weightNorm) && (
            <div className="mt-4 p-4 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-100 dark:border-slate-700">
              <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 mb-2">Normes de référence</p>
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
                {metrics.bmiNorm && (
                  <span className="text-slate-700 dark:text-slate-300">IMC recommandé: <strong>{metrics.bmiNorm}</strong></span>
                )}
                {metrics.weightNorm && (
                  <span className="text-slate-700 dark:text-slate-300">Poids recommandé: <strong>{metrics.weightNorm}</strong></span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Health Profile: derived meaning + chart */}
        {(metrics.bmi || metrics.bmiType != null || metrics.weight_s != null || metrics.bmi_s != null) && (
          <section className="space-y-3">
            <div className="flex items-center gap-2 px-1">
              <span className="material-icons-round text-emerald-600 text-lg">monitor_heart</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Profil santé</h3>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-6">
              {(metrics.bodyScore != null || metrics.bodyAge != null) && (
                <div className="grid grid-cols-2 gap-3">
                  {metrics.bodyScore != null && (
                    <div className="p-3 rounded-2xl bg-primary/5 dark:bg-accent-blue/10 border border-primary/10 dark:border-accent-blue/20">
                      <p className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">Score corporel</p>
                      <p className="text-2xl font-black text-primary dark:text-accent-blue mt-0.5">{metrics.bodyScore}<span className="text-sm font-bold text-slate-400">/100</span></p>
                    </div>
                  )}
                  {metrics.bodyAge != null && (
                    <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700">
                      <p className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400">Âge corporel</p>
                      <p className="text-2xl font-black text-slate-800 dark:text-white mt-0.5">{metrics.bodyAge} <span className="text-xs font-bold text-slate-400">ans</span></p>
                    </div>
                  )}
                </div>
              )}
              {/* Derived meaning from device codes */}
              <div className="grid grid-cols-2 gap-3">
                {getBMITypeLabel(metrics.bmiType) && (
                  <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Statut IMC (appareil)</p>
                    <p className={`text-lg font-black mt-0.5 ${
                      metrics.bmiType === '3' ? 'text-rose-600 dark:text-rose-400' :
                      metrics.bmiType === '2' ? 'text-amber-600 dark:text-amber-400' :
                      metrics.bmiType === '1' ? 'text-emerald-600 dark:text-emerald-400' :
                      'text-blue-600 dark:text-blue-400'
                    }`}>{getBMITypeLabel(metrics.bmiType)}</p>
                  </div>
                )}
                {getStatusLabel(metrics.weight_s) && (
                  <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Statut poids</p>
                    <p className="text-lg font-black text-slate-800 dark:text-white mt-0.5">{getStatusLabel(metrics.weight_s)}</p>
                  </div>
                )}
                {getStatusLabel(metrics.bmi_s) && (
                  <div className="p-3 rounded-2xl bg-slate-50 dark:bg-slate-900/50 border border-slate-100 dark:border-slate-700 col-span-2">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Interprétation IMC (appareil)</p>
                    <p className="text-base font-bold text-slate-700 dark:text-slate-300 mt-0.5">{getStatusLabel(metrics.bmi_s)}</p>
                  </div>
                )}
              </div>
              {/* BMI chart */}
              {metrics.bmi && (
                <div className="pt-4 border-t border-slate-100 dark:border-slate-700">
                  <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 mb-3">IMC vs norme</p>
                  <div className="h-24 w-full">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={[{ name: 'Votre IMC', value: parseFloat(metrics.bmi) || 0, fill: bmiInfo.color === 'rose' ? '#e11d48' : bmiInfo.color === 'amber' ? '#d97706' : bmiInfo.color === 'green' ? '#059669' : '#2563eb' }]} margin={{ top: 0, right: 8, left: 8, bottom: 0 }}>
                        <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                        <YAxis domain={[0, 40]} tick={{ fontSize: 10 }} />
                        <Tooltip formatter={(v) => [v, 'IMC']} />
                        <ReferenceLine y={18.5} stroke="#94a3b8" strokeDasharray="2 2" />
                        <ReferenceLine y={25} stroke="#94a3b8" strokeDasharray="2 2" />
                        <ReferenceLine y={30} stroke="#94a3b8" strokeDasharray="2 2" />
                        <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                          <Cell fill={bmiInfo.category === 'obesity' ? '#e11d48' : bmiInfo.category === 'overweight' ? '#d97706' : bmiInfo.category === 'normal' ? '#059669' : '#2563eb'} />
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="flex justify-between text-[8px] text-slate-400 dark:text-slate-500 mt-1 px-1">
                    <span>0</span>
                    <span>18.5</span>
                    <span>25</span>
                    <span>30</span>
                    <span>40</span>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Physical Metrics Section */}
        {(metrics.height || metrics.weight || metrics.bmi) && (
          <section className="space-y-3">
            <div className="flex items-center gap-2 px-1">
              <span className="material-icons-round text-primary dark:text-accent-blue text-lg">straighten</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Mesures Physiques</h3>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-6">
              {(metrics.height || metrics.weight) && (
                <div className="grid grid-cols-2 gap-6">
                  {metrics.height && (
                    <div className="space-y-1">
                      <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Taille</p>
                      <p className="text-3xl font-black text-primary dark:text-accent-blue">
                        {metrics.height}<span className="text-xs font-bold text-slate-400 ml-1 uppercase">cm</span>
                      </p>
                    </div>
                  )}
                  {metrics.weight && (
                    <div className="space-y-1 border-l border-slate-100 dark:border-slate-700 pl-6">
                      <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Poids</p>
                      <p className="text-3xl font-black text-primary dark:text-accent-blue">
                        {metrics.weight}<span className="text-xs font-bold text-slate-400 ml-1 uppercase">kg</span>
                      </p>
                    </div>
                  )}
                </div>
              )}

              {metrics.bmi && (
                <div className="pt-6 border-t border-slate-100 dark:border-slate-700">
                  <div className="flex justify-between items-end mb-4">
                    <div>
                      <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500 mb-1">Indice de Masse Corporelle</p>
                      <p className="text-4xl font-black text-slate-900 dark:text-white">{metrics.bmi}</p>
                    </div>
                    <span className={`text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-wider ${
                      bmiInfo.category === 'normal' ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-400' :
                      bmiInfo.category === 'overweight' ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-400' :
                      bmiInfo.category === 'obesity' ? 'bg-rose-100 dark:bg-rose-900/40 text-rose-700 dark:text-rose-400' :
                      bmiInfo.category === 'underweight' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400' :
                      'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                    }`}>
                      {bmiInfo.label}
                    </span>
                  </div>
                  <div className="relative pt-2 pb-2">
                    <div className="h-2 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden flex">
                      <div className="h-full bg-blue-400" style={{ width: '18.5%' }}></div>
                      <div className="h-full bg-emerald-400" style={{ width: '25%' }}></div>
                      <div className="h-full bg-amber-400" style={{ width: '25%' }}></div>
                      <div className="h-full bg-rose-400" style={{ width: '31.5%' }}></div>
                    </div>
                    <div className="absolute top-0 transition-all duration-1000 ease-out" style={{ left: `${bmiGaugePosition}%` }}>
                      <div className="w-1.5 h-4 bg-primary dark:bg-white rounded-full -translate-x-1/2 shadow-sm"></div>
                    </div>
                  </div>
                  <div className="flex justify-between text-[8px] font-black text-slate-400 dark:text-slate-600 px-0.5 uppercase tracking-widest mt-1">
                    <span>18.5</span>
                    <span>25</span>
                    <span>30</span>
                    <span>35+</span>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Cardiovascular Section */}
        {(systolic || diastolic || metrics.heartRate || metrics.oxygen) && (
          <section className="space-y-3">
            <div className="flex items-center gap-2 px-1">
              <span className="material-icons-round text-rose-500 text-lg">favorite</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Cardiovasculaire</h3>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-6">
              {(systolic || diastolic) && (
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Pression Artérielle</p>
                    <div className="flex items-baseline gap-1">
                      {systolic && <span className="text-4xl font-black text-slate-900 dark:text-white">{systolic}</span>}
                      {(systolic && diastolic) && <span className="text-2xl font-bold text-slate-200 dark:text-slate-700 mx-1">/</span>}
                      {diastolic && <span className="text-4xl font-black text-slate-900 dark:text-white">{diastolic}</span>}
                      <span className="text-xs font-bold text-slate-400 ml-2 uppercase">mmHg</span>
                    </div>
                  </div>
                  <div className="bg-rose-50 dark:bg-rose-900/20 text-rose-500 p-3 rounded-2xl">
                    <span className="material-icons-round text-3xl">monitor_heart</span>
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-6 pt-6 border-t border-slate-100 dark:border-slate-700">
                {metrics.heartRate && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Pouls</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-black text-rose-500">{metrics.heartRate}</span>
                      <span className="text-xs font-bold text-slate-400 ml-1 uppercase">bpm</span>
                    </div>
                  </div>
                )}
                {metrics.oxygen && (
                  <div className="space-y-1 border-l border-slate-100 dark:border-slate-700 pl-6">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">SpO2</p>
                    <div className="flex items-baseline gap-1">
                      <span className="text-3xl font-black text-blue-500">{metrics.oxygen}</span>
                      <span className="text-xs font-bold text-slate-400 ml-1 uppercase">%</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* Body Composition Section */}
        {hasBodyComposition && (
          <section className="space-y-3">
            <div className="flex items-center gap-2 px-1">
              <span className="material-icons-round text-indigo-500 text-lg">analytics</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Composition Corporelle</h3>
            </div>
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700">
              <div className="grid grid-cols-2 gap-y-6 gap-x-4">
                {metrics.fatRate && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Masse Grasse</p>
                    <p className="text-2xl font-black text-slate-800 dark:text-white">{metrics.fatRate}%</p>
                  </div>
                )}
                {metrics.waterRate && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Hydratation</p>
                    <p className="text-2xl font-black text-slate-800 dark:text-white">{metrics.waterRate}%</p>
                  </div>
                )}
                {metrics.muscleRate && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Masse Musculaire</p>
                    <p className="text-2xl font-black text-slate-800 dark:text-white">{metrics.muscleRate}%</p>
                  </div>
                )}
                {metrics.visceralFat && (
                  <div className="space-y-1">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Graisse Viscérale</p>
                    <p className="text-2xl font-black text-slate-800 dark:text-white">{metrics.visceralFat}</p>
                  </div>
                )}
                {metrics.metabolism && (
                  <div className="space-y-1 col-span-2 pt-2">
                    <p className="text-[10px] font-bold uppercase text-slate-400 dark:text-slate-500">Métabolisme de Base</p>
                    <p className="text-2xl font-black text-slate-800 dark:text-white">{metrics.metabolism} kcal</p>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* AI Analysis Section */}
        <section className="space-y-3">
          <div className="flex items-center justify-between flex-wrap gap-2 px-1">
            <div className="flex items-center gap-2">
              <span className="material-icons-round text-amber-500 text-lg">auto_awesome</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Analyse IA</h3>
            </div>
            {!analysis && !loadingAnalysis && (
              <button
                onClick={handleAnalyze}
                className="text-[10px] font-black uppercase text-primary dark:text-accent-blue bg-primary/5 dark:bg-accent-blue/5 px-3 py-1.5 rounded-full border border-primary/10 dark:border-accent-blue/10"
              >
                Générer l&apos;analyse
              </button>
            )}
            {analysis && !loadingAnalysis && (
              <button
                onClick={() => setAnalysis(null)}
                className="text-[10px] font-bold uppercase text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
              >
                Nouvelle analyse
              </button>
            )}
          </div>

          {loadingAnalysis ? (
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-8 shadow-sm border border-slate-200 dark:border-slate-700 flex flex-col items-center justify-center gap-4">
              <div className="w-8 h-8 border-4 border-primary/20 border-t-primary rounded-full animate-spin"></div>
              <p className="text-xs font-bold text-slate-400 uppercase tracking-widest animate-pulse">Analyse en cours...</p>
            </div>
          ) : analysis ? (
            <div className="bg-white dark:bg-slate-800 rounded-3xl p-6 shadow-sm border border-slate-200 dark:border-slate-700 space-y-6 animate-fade-in">
              {analysis.error ? (
                <div className="p-5 bg-rose-50 dark:bg-rose-900/20 rounded-2xl border border-rose-100 dark:border-rose-800/30 space-y-3">
                  <p className="text-sm font-medium text-rose-700 dark:text-rose-300 leading-relaxed">
                    {analysis.interpretation || analysis.error}
                  </p>
                  <button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={loadingAnalysis}
                    className="text-xs font-bold text-rose-600 dark:text-rose-400 hover:underline"
                  >
                    Réessayer l&apos;analyse
                  </button>
                </div>
              ) : (
                <>
                  {/* Summary */}
                  {analysis.summary && (
                    <div className="space-y-2">
                      <p className="text-[10px] font-bold uppercase text-slate-400 tracking-widest">Résumé</p>
                      <p className="text-sm font-bold text-slate-700 dark:text-slate-200 leading-relaxed">{analysis.summary}</p>
                    </div>
                  )}

                  {/* Body age comment */}
                  {analysis.body_age_comment && (
                    <div className="flex gap-3 items-start p-3 bg-indigo-50 dark:bg-indigo-900/20 rounded-2xl border border-indigo-100 dark:border-indigo-800/30">
                      <span className="material-icons-round text-indigo-500 text-sm mt-0.5 flex-shrink-0">psychology</span>
                      <p className="text-xs text-indigo-700 dark:text-indigo-300 leading-relaxed">{analysis.body_age_comment}</p>
                    </div>
                  )}

                  {/* Anomalies */}
                  {analysis.anomalies?.length > 0 && (
                    <div className="space-y-2 pt-4 border-t border-slate-50 dark:border-slate-700/50">
                      <p className="text-[10px] font-bold uppercase text-slate-400 tracking-widest">Points d'attention</p>
                      <div className="space-y-2">
                        {analysis.anomalies.map((a, i) => (
                          <div key={i} className="flex gap-3 items-start">
                            <span className="material-icons-round text-amber-500 text-sm mt-0.5 flex-shrink-0">warning_amber</span>
                            <p className="text-xs text-slate-600 dark:text-slate-400">{a}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sections */}
                  {analysis.sections && Object.entries(analysis.sections).filter(([, v]) => v).length > 0 && (
                    <div className="space-y-4 pt-4 border-t border-slate-50 dark:border-slate-700/50">
                      {[
                        { key: 'imc_poids',            label: 'IMC & Poids',             icon: 'monitor_weight' },
                        { key: 'composition_graisses', label: 'Masse grasse',             icon: 'water_drop' },
                        { key: 'composition_muscle_eau',label: 'Muscle & Hydratation',    icon: 'fitness_center' },
                        { key: 'metabolisme',          label: 'Métabolisme',              icon: 'local_fire_department' },
                        { key: 'cardiovasculaire',     label: 'Cardiovasculaire',         icon: 'favorite' },
                      ].map(({ key, label, icon }) =>
                        analysis.sections[key] ? (
                          <div key={key} className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="material-icons-round text-primary dark:text-accent-blue text-sm">{icon}</span>
                              <p className="text-[10px] font-bold uppercase text-slate-400 tracking-widest">{label}</p>
                            </div>
                            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed pl-6">{analysis.sections[key]}</p>
                          </div>
                        ) : null
                      )}
                    </div>
                  )}

                  {/* Recommendations */}
                  {(analysis.recommendations?.length > 0 || analysis.advice?.length > 0) && (
                    <div className="space-y-3 pt-4 border-t border-slate-50 dark:border-slate-700/50">
                      <p className="text-[10px] font-bold uppercase text-slate-400 tracking-widest">Conseils personnalisés</p>
                      <div className="space-y-2">
                        {(analysis.recommendations?.length > 0 ? analysis.recommendations : analysis.advice?.map(a => ({ conseil: a }))).map((rec, i) => (
                          <div key={i} className="flex gap-3 items-start p-3 rounded-2xl bg-emerald-50 dark:bg-emerald-900/10 border border-emerald-100 dark:border-emerald-800/20">
                            <span className="material-icons-round text-emerald-500 text-sm mt-0.5 flex-shrink-0">check_circle</span>
                            <div className="flex-1 min-w-0">
                              {rec.domaine && (
                                <p className="text-[9px] font-black uppercase text-emerald-600 dark:text-emerald-400 tracking-wider mb-0.5">{rec.domaine}</p>
                              )}
                              <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">{rec.conseil || rec}</p>
                            </div>
                            {rec.priorite === 'haute' && (
                              <span className="text-[8px] font-black uppercase bg-rose-100 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400 px-1.5 py-0.5 rounded-full flex-shrink-0">Urgent</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Disclaimer */}
                  {analysis.disclaimer && (
                    <p className="text-[10px] text-slate-400 dark:text-slate-500 leading-relaxed pt-2 border-t border-slate-50 dark:border-slate-700/50">
                      ⚕️ {analysis.disclaimer}
                    </p>
                  )}
                </>
              )}
            </div>
          ) : null}
        </section>

        <div className="space-y-3 pt-4">
          <div className="p-4 bg-slate-50 dark:bg-slate-900/50 rounded-2xl border border-slate-200 dark:border-slate-700">
            <p className="text-[10px] font-bold uppercase text-slate-500 dark:text-slate-400 mb-2">Envoyer le rapport par e-mail</p>
            <p className="text-xs text-slate-600 dark:text-slate-300 mb-3">Entrez l&apos;adresse du client (ex. après mesure sur kiosque) pour lui envoyer le rapport avec lien.</p>
            <div className="flex gap-2">
              <input
                type="email"
                value={sendToEmail}
                onChange={(e) => setSendToEmail(e.target.value)}
                placeholder="client@exemple.com"
                className="flex-1 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 text-sm"
              />
              <button
                type="button"
                onClick={handleSendToEmail}
                disabled={sendingToEmail || !sendToEmail?.trim()}
                className="px-4 py-2 rounded-xl bg-rose-500 text-white text-xs font-bold disabled:opacity-50"
              >
                {sendingToEmail ? 'Envoi...' : 'Envoyer'}
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={handlePrint}
              className="flex flex-col items-center justify-center gap-2 p-6 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-3xl active:scale-95 transition-all shadow-sm"
            >
              <div className="w-10 h-10 bg-primary/10 dark:bg-accent-blue/20 rounded-2xl flex items-center justify-center">
                <span className="material-icons-round text-primary dark:text-accent-blue">print</span>
              </div>
              <span className="text-xs font-bold text-slate-700 dark:text-slate-200">Imprimer</span>
            </button>
            <button
              onClick={handleEmail}
              disabled={sendingEmail}
              className="flex flex-col items-center justify-center gap-2 p-6 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-3xl active:scale-95 transition-all shadow-sm disabled:opacity-50"
            >
              <div className="w-10 h-10 bg-rose-500/10 rounded-2xl flex items-center justify-center">
                {sendingEmail ? (
                  <div className="w-5 h-5 border-2 border-rose-500/30 border-t-rose-500 rounded-full animate-spin"></div>
                ) : (
                  <span className="material-icons-round text-rose-500">mail</span>
                )}
              </div>
              <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
                {sendingEmail ? 'Envoi...' : 'Email client lié'}
              </span>
            </button>
          </div>
        </div>

        <p className="text-[10px] text-center text-slate-400 dark:text-slate-600 px-10 leading-relaxed font-medium">
          Ce rapport est généré automatiquement. Consultez un professionnel de santé pour une analyse médicale approfondie.
        </p>
      </main>

      <footer className="fixed bottom-0 w-full bg-white/90 dark:bg-slate-900/90 ios-blur border-t border-slate-200 dark:border-slate-800 px-6 py-2 pb-6 flex justify-between items-center z-50">
        <button onClick={() => navigate('/')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">dashboard</span>
          <span className="text-[10px] font-medium">Accueil</span>
        </button>
        <button onClick={() => navigate('/dashboard')} className="flex flex-col items-center gap-1 text-primary dark:text-accent-blue">
          <span className="material-icons-round">description</span>
          <span className="text-[10px] font-bold">Rapports</span>
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

export default ReportDetail;
