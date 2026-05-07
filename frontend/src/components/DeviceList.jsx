import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import autoAnimate from '@formkit/auto-animate';
import { deviceApi, adminApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const DeviceList = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [devices, setDevices] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newDevice, setNewDevice] = useState({ device_id: '', name: '' });
  const [editingDeviceId, setEditingDeviceId] = useState(null);
  const [draftOwnerIds, setDraftOwnerIds] = useState([]);
  const [saving, setSaving] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current && autoAnimate(listRef.current);
  }, [listRef]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [devicesData, usersData] = await Promise.all([
        deviceApi.getDevices(),
        user.role === 'admin' ? adminApi.getAllUsers() : Promise.resolve([])
      ]);
      setDevices(devicesData);
      setUsers(usersData);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddDevice = async (e) => {
    e.preventDefault();
    try {
      await deviceApi.createDevice(newDevice);
      setShowAddModal(false);
      setNewDevice({ device_id: '', name: '' });
      loadData();
    } catch (error) {
      console.error('Error creating device:', error);
      alert('Erreur lors de l\'enregistrement de l\'appareil');
    }
  };

  const startEditOwners = (device) => {
    setEditingDeviceId(device.id);
    setDraftOwnerIds(Array.isArray(device.owner_ids) ? [...device.owner_ids] : []);
  };

  const cancelEditOwners = () => {
    setEditingDeviceId(null);
    setDraftOwnerIds([]);
  };

  const addOwner = (userId) => {
    if (userId && !draftOwnerIds.includes(userId)) setDraftOwnerIds([...draftOwnerIds, userId]);
  };

  const removeOwner = (userId) => {
    setDraftOwnerIds(draftOwnerIds.filter((id) => id !== userId));
  };

  const saveOwners = async () => {
    if (editingDeviceId == null) return;
    setSaving(true);
    try {
      await deviceApi.setDeviceOwners(editingDeviceId, draftOwnerIds);
      setEditingDeviceId(null);
      setDraftOwnerIds([]);
      loadData();
    } catch (error) {
      console.error('Error saving owners:', error);
      const msg = error.response?.data?.detail || error.message || 'Erreur lors de l\'enregistrement';
      alert(Array.isArray(msg) ? msg.join(', ') : msg);
    } finally {
      setSaving(false);
    }
  };

  const ownerIdsFor = (device) =>
    editingDeviceId === device.id ? draftOwnerIds : (device.owner_ids || []);
  const isEditing = (device) => editingDeviceId === device.id;
  const userById = (id) => users.find((u) => u.id === id);

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
          <h1 className="text-lg font-bold tracking-tight text-primary dark:text-white">
            {user.role === 'admin' ? 'Gestion des Appareils' : 'Mes Appareils'}
          </h1>
        </div>
        {user.role === 'admin' && (
          <button 
            onClick={() => setShowAddModal(true)}
            className="p-2 bg-primary/10 dark:bg-accent-blue/20 rounded-full text-primary dark:text-accent-blue flex items-center gap-1 px-3"
          >
            <span className="material-icons-round text-sm">add</span>
            <span className="text-xs font-bold uppercase tracking-wider">Ajouter</span>
          </button>
        )}
      </nav>

      <main className="p-4 max-w-md mx-auto space-y-4">
        {user.role === 'admin' && (
          <div className="bg-primary/5 dark:bg-accent-blue/5 border border-primary/10 dark:border-accent-blue/10 p-4 rounded-2xl mb-2">
            <p className="text-[10px] font-bold uppercase text-primary dark:text-accent-blue tracking-widest mb-1">Espace Administrateur</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">Enregistrez des appareils et assignez un ou plusieurs propriétaires par appareil. Cliquez sur « Modifier les propriétaires » puis « Enregistrer les propriétaires » pour sauvegarder.</p>
          </div>
        )}
        {loading ? (
          <div className="text-center py-10 text-slate-500 font-medium">Chargement...</div>
        ) : devices.length === 0 ? (
          <div className="text-center py-20 space-y-4">
            <div className="w-20 h-20 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto text-slate-300 dark:text-slate-600">
              <span className="material-icons-round text-5xl">devices_other</span>
            </div>
            <p className="text-slate-500 font-medium text-sm">Aucun appareil enregistré</p>
            {user.role === 'admin' && (
              <button 
                onClick={() => setShowAddModal(true)}
                className="px-6 py-3 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold text-sm shadow-lg shadow-primary/20"
              >
                Enregistrer un Appareil
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4" ref={listRef}>
            {devices.map((device) => (
              <div 
                key={device.id}
                className="bg-white dark:bg-slate-800 p-6 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm space-y-4"
              >
                <div className="flex items-center gap-4">
                  <div className="h-12 w-12 rounded-2xl bg-slate-50 dark:bg-slate-900 flex items-center justify-center border border-slate-100 dark:border-slate-700 flex-shrink-0">
                    <span className="material-icons-round text-2xl text-slate-400">devices</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-slate-900 dark:text-white truncate">{device.name || 'Appareil sans nom'}</h3>
                      {device.device_model && (
                        <span className="px-2 py-0.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-full text-[9px] font-black uppercase tracking-wider border border-indigo-100 dark:border-indigo-800/30 flex-shrink-0">
                          {device.device_model}
                        </span>
                      )}
                    </div>
                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{device.device_id}</p>
                    {device.mac_addr && (
                      <p className="text-[9px] text-slate-400 font-mono mt-0.5">{device.mac_addr}</p>
                    )}
                  </div>
                  {(ownerIdsFor(device).length === 0) ? (
                    <span className="px-3 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 rounded-full text-[10px] font-bold uppercase tracking-wider border border-emerald-100 dark:border-emerald-800/30 flex-shrink-0">
                      🌍 Public
                    </span>
                  ) : (
                    <span className="px-3 py-1 bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded-full text-[10px] font-bold uppercase tracking-wider border border-blue-100 dark:border-blue-800/30 flex-shrink-0">
                      👤 {ownerIdsFor(device).length} propriétaire(s)
                    </span>
                  )}
                </div>
                {(device.unit_name || device.unit_no) && (
                  <div className="flex gap-3 text-[10px] text-slate-400 px-1">
                    {device.unit_name && <span>📍 {device.unit_name}</span>}
                    {device.unit_no   && <span className="font-mono">Unité #{device.unit_no}</span>}
                  </div>
                )}

                {user.role === 'admin' && (
                  <div className="pt-4 border-t border-slate-50 dark:border-slate-700 space-y-3">
                    <p className="text-[10px] font-bold uppercase text-slate-400 tracking-wider">
                      Propriétaires (accès aux mesures)
                    </p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      Aucun = appareil public. Ajoutez des utilisateurs puis enregistrez.
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {ownerIdsFor(device).map((uid) => {
                        const u = userById(uid);
                        return (
                          <span
                            key={uid}
                            className="inline-flex items-center gap-1 px-3 py-1.5 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 rounded-xl text-xs font-medium border border-blue-100 dark:border-blue-800/30"
                          >
                            {u ? u.email : uid}
                            {isEditing(device) && (
                              <button
                                type="button"
                                onClick={() => removeOwner(uid)}
                                className="p-0.5 rounded-full hover:bg-blue-200 dark:hover:bg-blue-800/40"
                                aria-label="Retirer"
                              >
                                <span className="material-icons-round text-sm">close</span>
                              </button>
                            )}
                          </span>
                        );
                      })}
                    </div>
                    {isEditing(device) && (
                      <>
                        <div className="flex flex-wrap gap-2 items-center">
                          <label className="text-[10px] font-bold text-slate-500">Ajouter :</label>
                          <select
                          value=""
                          onChange={(e) => { const v = e.target.value; if (v) addOwner(v); e.target.value = ''; }}
                          className="flex-1 min-w-0 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs py-2 px-3 font-medium"
                        >
                          <option value="">— Choisir un utilisateur —</option>
                          {users.filter((u) => !draftOwnerIds.includes(u.id)).map((u) => (
                            <option key={u.id} value={u.id}>{u.email} ({u.role})</option>
                          ))}
                        </select>
                        </div>
                        {draftOwnerIds.length > 0 && (
                          <button
                            type="button"
                            onClick={() => setDraftOwnerIds([])}
                            className="text-[11px] font-medium text-slate-500 dark:text-slate-400 hover:text-emerald-600 dark:hover:text-emerald-400"
                          >
                            Tout retirer → appareil public
                          </button>
                        )}
                      </>
                    )}
                    <div className="flex gap-2 pt-1">
                      {!isEditing(device) ? (
                        <button
                          type="button"
                          onClick={() => startEditOwners(device)}
                          className="py-2 px-4 rounded-xl text-xs font-bold text-primary dark:text-accent-blue bg-primary/10 dark:bg-accent-blue/10 border border-primary/20 dark:border-accent-blue/20"
                        >
                          Modifier les propriétaires
                        </button>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={saveOwners}
                            disabled={saving}
                            className="py-2 px-4 rounded-xl text-xs font-bold text-white bg-primary dark:bg-accent-blue disabled:opacity-50"
                          >
                            {saving ? 'Enregistrement…' : 'Enregistrer les propriétaires'}
                          </button>
                          <button
                            type="button"
                            onClick={cancelEditOwners}
                            className="py-2 px-4 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700"
                          >
                            Annuler
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}
                <div className="pt-3 border-t border-slate-50 dark:border-slate-700">
                  <button
                    type="button"
                    onClick={() => navigate(`/dashboard?device_id=${encodeURIComponent(device.device_id)}`)}
                    className="w-full py-2 rounded-xl text-xs font-bold text-primary dark:text-accent-blue bg-primary/5 dark:bg-accent-blue/5 border border-primary/10 dark:border-accent-blue/10 flex items-center justify-center gap-2"
                  >
                    <span className="material-icons-round text-sm">description</span>
                    Voir les mesures de cet appareil
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-800 w-full max-w-md rounded-t-[2.5rem] sm:rounded-3xl p-8 space-y-6 shadow-2xl animate-slide-up">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-black text-slate-900 dark:text-white">Nouvel Appareil</h2>
              <button onClick={() => setShowAddModal(false)} className="p-2 bg-slate-100 dark:bg-slate-700 rounded-full text-slate-500">
                <span className="material-icons-round">close</span>
              </button>
            </div>

            <form onSubmit={handleAddDevice} className="space-y-6">
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">ID Appareil (Device ID)</label>
                <input
                  type="text"
                  required
                  value={newDevice.device_id}
                  onChange={(e) => setNewDevice({ ...newDevice, device_id: e.target.value })}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl outline-none focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue text-sm"
                  placeholder="Ex: KIOSK-001"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">Nom de l'Appareil</label>
                <input
                  type="text"
                  value={newDevice.name}
                  onChange={(e) => setNewDevice({ ...newDevice, name: e.target.value })}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl outline-none focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue text-sm"
                  placeholder="Ex: Entrée Pharmacie A"
                />
              </div>

              <button
                type="submit"
                className="w-full py-4 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold shadow-lg shadow-primary/20 active:scale-95 transition-all"
              >
                Enregistrer l'Appareil
              </button>
            </form>
          </div>
        </div>
      )}

      <footer className="fixed bottom-0 w-full bg-white/90 dark:bg-slate-900/90 ios-blur border-t border-slate-200 dark:border-slate-800 px-6 py-2 pb-6 flex justify-between items-center z-50">
        <button onClick={() => navigate('/dashboard')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">dashboard</span>
          <span className="text-[10px] font-medium">Accueil</span>
        </button>
        <button onClick={() => navigate('/dashboard')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">description</span>
          <span className="text-[10px] font-medium">Rapports</span>
        </button>
        <button onClick={() => navigate('/customers')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">groups</span>
          <span className="text-[10px] font-medium">Patients</span>
        </button>
        <button onClick={() => navigate('/devices')} className="flex flex-col items-center gap-1 text-primary dark:text-accent-blue">
          <span className="material-icons-round">settings_remote</span>
          <span className="text-[10px] font-bold">Appareils</span>
        </button>
      </footer>
    </div>
  );
};

export default DeviceList;

