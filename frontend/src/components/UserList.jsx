import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import autoAnimate from '@formkit/auto-animate';
import { adminApi } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const ROLES = [
  { value: 'regular', label: 'Utilisateur', desc: 'Accès standard' },
  { value: 'customer', label: 'Propriétaire machine', desc: 'V2: organisations, emplacements' },
  { value: 'staff', label: 'Staff', desc: 'Équipe interne' },
  { value: 'admin', label: 'Administrateur', desc: 'Accès complet' },
  { value: 'retail', label: 'Retail', desc: 'V2: utilisateur invité' },
];

const UserList = () => {
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createEmail, setCreateEmail] = useState('');
  const [createRole, setCreateRole] = useState('customer');
  const [createSendPin, setCreateSendPin] = useState(true);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState('');
  const [editingId, setEditingId] = useState(null);
  const [editRole, setEditRole] = useState('');
  const [editActive, setEditActive] = useState(true);
  const [editWhatsapp, setEditWhatsapp] = useState('');
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current && autoAnimate(listRef.current);
  }, [listRef]);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      setLoading(true);
      const data = await adminApi.getAllUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error loading users:', err);
      setUsers([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setCreateError('');
    setCreateSubmitting(true);
    try {
      await adminApi.createUser(createEmail.trim(), createRole, createSendPin);
      setShowCreateModal(false);
      setCreateEmail('');
      setCreateRole('customer');
      setCreateSendPin(true);
      loadUsers();
    } catch (err) {
      setCreateError(err.response?.data?.detail || 'Erreur lors de la création du compte.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const startEdit = (u) => {
    setEditingId(u.id);
    setEditRole(u.role);
    setEditActive(u.is_active);
    setEditWhatsapp(u.whatsapp_phone_e164 || '');
  };

  const cancelEdit = () => {
    setEditingId(null);
  };

  const saveEdit = async (userId) => {
    try {
      await adminApi.updateUser(userId, {
        role: editRole,
        is_active: editActive,
        whatsapp_phone_e164: editWhatsapp.trim() || null,
      });
      setEditingId(null);
      loadUsers();
    } catch (err) {
      console.error('Error updating user:', err);
      alert(err.response?.data?.detail || 'Erreur lors de la mise à jour.');
    }
  };

  const handleDelete = async (u) => {
    if (u.id === currentUser?.id) {
      alert('Vous ne pouvez pas supprimer votre propre compte.');
      return;
    }
    if (!window.confirm(`Supprimer l'utilisateur ${u.email} ? Cette action est irréversible.`)) return;
    try {
      await adminApi.deleteUser(u.id);
      loadUsers();
    } catch (err) {
      alert(err.response?.data?.detail || 'Erreur lors de la suppression.');
    }
  };

  const formatDate = (d) => {
    if (!d) return '—';
    return new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  const formatDateTime = (d) => {
    if (!d) return null;
    const date = new Date(d);
    const day = date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
    const time = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
    return `${day} à ${time}`;
  };

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
            Gestion des utilisateurs
          </h1>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="p-2 bg-primary/10 dark:bg-accent-blue/20 rounded-full text-primary dark:text-accent-blue flex items-center gap-1 px-3"
        >
          <span className="material-icons-round text-sm">person_add</span>
          <span className="text-xs font-bold uppercase tracking-wider">Créer</span>
        </button>
      </nav>

      <main className="p-4 max-w-md mx-auto space-y-4">
        <div className="bg-primary/5 dark:bg-accent-blue/5 border border-primary/10 dark:border-accent-blue/10 p-4 rounded-2xl mb-2">
          <p className="text-[10px] font-bold uppercase text-primary dark:text-accent-blue tracking-widest mb-1">Espace Administrateur</p>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Créez des comptes par e-mail (ex. propriétaire machine avec rôle &quot;Propriétaire machine&quot;), modifiez les rôles et activez/désactivez les comptes.
          </p>
        </div>

        {loading ? (
          <div className="text-center py-10 text-slate-500 font-medium">Chargement...</div>
        ) : users.length === 0 ? (
          <div className="text-center py-20 space-y-4">
            <div className="w-20 h-20 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto text-slate-300 dark:text-slate-600">
              <span className="material-icons-round text-5xl">people</span>
            </div>
            <p className="text-slate-500 font-medium text-sm">Aucun utilisateur</p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-6 py-3 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold text-sm shadow-lg shadow-primary/20"
            >
              Créer un utilisateur
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4" ref={listRef}>
            {users.map((u) => (
              <div
                key={u.id}
                className="bg-white dark:bg-slate-800 p-5 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm space-y-3"
              >
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-2xl bg-slate-50 dark:bg-slate-900 flex items-center justify-center border border-slate-100 dark:border-slate-700 flex-shrink-0">
                    <span className="material-icons-round text-2xl text-slate-400">person</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-slate-900 dark:text-white truncate">{u.email}</p>
                    <p className="text-[10px] text-slate-400 uppercase tracking-wider">
                      {ROLES.find((r) => r.value === u.role)?.label || u.role} · {u.is_active ? 'Actif' : 'Inactif'}
                    </p>
                    <p className="text-[9px] text-slate-400 mt-0.5">
                      Créé le {formatDate(u.created_at)}
                      {formatDateTime(u.last_login) && (
                        <> · Dernière connexion le {formatDateTime(u.last_login)}</>
                      )}
                    </p>
                    {u.whatsapp_phone_e164 && (
                      <p className="text-[9px] text-emerald-600 dark:text-emerald-400 mt-1 font-mono">
                        WhatsApp : {u.whatsapp_phone_e164}
                      </p>
                    )}
                  </div>
                  {u.id === currentUser?.id && (
                    <span className="px-2 py-0.5 bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 rounded-full text-[9px] font-bold uppercase">Vous</span>
                  )}
                </div>

                {editingId === u.id ? (
                  <div className="pt-3 border-t border-slate-100 dark:border-slate-700 space-y-3">
                    <div>
                      <label className="text-[8px] font-black uppercase text-slate-400 tracking-wider ml-1">Rôle</label>
                      <select
                        value={editRole}
                        onChange={(e) => setEditRole(e.target.value)}
                        className="w-full mt-1 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs py-2 px-3 font-bold text-slate-700 dark:text-slate-200"
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value}>{r.label}</option>
                        ))}
                      </select>
                    </div>
                    <label className="flex items-center gap-2 text-xs font-medium text-slate-600 dark:text-slate-300">
                      <input
                        type="checkbox"
                        checked={editActive}
                        onChange={(e) => setEditActive(e.target.checked)}
                        className="rounded border-slate-300 text-primary"
                      />
                      Compte actif
                    </label>
                    <div>
                      <label className="text-[8px] font-black uppercase text-slate-400 tracking-wider ml-1">
                        WhatsApp (E.164, PDF rapport)
                      </label>
                      <input
                        type="text"
                        value={editWhatsapp}
                        onChange={(e) => setEditWhatsapp(e.target.value)}
                        placeholder="+33612345678"
                        className="w-full mt-1 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs py-2 px-3 font-mono text-slate-700 dark:text-slate-200"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => saveEdit(u.id)}
                        className="flex-1 py-2 rounded-xl text-xs font-bold text-white bg-primary dark:bg-accent-blue"
                      >
                        Enregistrer
                      </button>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        className="flex-1 py-2 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-700"
                      >
                        Annuler
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="pt-3 border-t border-slate-100 dark:border-slate-700 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => startEdit(u)}
                      className="py-2 px-3 rounded-xl text-xs font-bold text-primary dark:text-accent-blue bg-primary/5 dark:bg-accent-blue/5 border border-primary/10 dark:border-accent-blue/10"
                    >
                      Modifier
                    </button>
                    {u.id !== currentUser?.id && (
                      <button
                        type="button"
                        onClick={() => handleDelete(u)}
                        className="py-2 px-3 rounded-xl text-xs font-bold text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-900/20 border border-rose-100 dark:border-rose-800/30"
                      >
                        Supprimer
                      </button>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create user modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-slate-800 w-full max-w-md rounded-t-[2.5rem] sm:rounded-3xl p-8 space-y-6 shadow-2xl animate-slide-up">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-black text-slate-900 dark:text-white">Nouvel utilisateur</h2>
              <button onClick={() => { setShowCreateModal(false); setCreateError(''); }} className="p-2 bg-slate-100 dark:bg-slate-700 rounded-full text-slate-500">
                <span className="material-icons-round">close</span>
              </button>
            </div>

            <form onSubmit={handleCreateUser} className="space-y-6">
              {createError && (
                <div className="p-3 rounded-2xl bg-rose-50 dark:bg-rose-900/20 border border-rose-100 dark:border-rose-800/30 text-rose-700 dark:text-rose-400 text-sm">
                  {createError}
                </div>
              )}
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">E-mail</label>
                <input
                  type="email"
                  required
                  value={createEmail}
                  onChange={(e) => setCreateEmail(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl outline-none focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue text-sm"
                  placeholder="exemple@domaine.com"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">Rôle</label>
                <select
                  value={createRole}
                  onChange={(e) => setCreateRole(e.target.value)}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl outline-none focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue text-sm"
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label} – {r.desc}</option>
                  ))}
                </select>
              </div>
              <label className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
                <input
                  type="checkbox"
                  checked={createSendPin}
                  onChange={(e) => setCreateSendPin(e.target.checked)}
                  className="rounded border-slate-300 text-primary"
                />
                Envoyer un code PIN par e-mail (connexion possible tout de suite)
              </label>
              <button
                type="submit"
                disabled={createSubmitting}
                className="w-full py-4 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold shadow-lg shadow-primary/20 active:scale-95 transition-all disabled:opacity-50"
              >
                {createSubmitting ? 'Création…' : 'Créer l\'utilisateur'}
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
        <button onClick={() => navigate('/devices')} className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">settings_remote</span>
          <span className="text-[10px] font-medium">Appareils</span>
        </button>
        <button onClick={() => navigate('/users')} className="flex flex-col items-center gap-1 text-primary dark:text-accent-blue">
          <span className="material-icons-round">people</span>
          <span className="text-[10px] font-bold">Utilisateurs</span>
        </button>
      </footer>
    </div>
  );
};

export default UserList;
