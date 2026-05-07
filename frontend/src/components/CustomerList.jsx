import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import autoAnimate from '@formkit/auto-animate';
import imageCompression from 'browser-image-compression';
import { customerApi, getFileUrl } from '../services/api';

const CustomerList = () => {
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [isCompressing, setIsCompressing] = useState(false);
  const [newCustomer, setNewCustomer] = useState({ 
    full_name: '', 
    email: '', 
    dob: '', 
    photo: null 
  });
  const listRef = useRef(null);

  useEffect(() => {
    listRef.current && autoAnimate(listRef.current);
  }, [listRef]);

  useEffect(() => {
    loadCustomers();
  }, []);

  const handlePhotoChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      setIsCompressing(true);
      const options = {
        maxSizeMB: 0.2, // Max 200KB
        maxWidthOrHeight: 800,
        useWebWorker: true,
      };
      const compressedFile = await imageCompression(file, options);
      setNewCustomer({ ...newCustomer, photo: compressedFile });
    } catch (error) {
      console.error('Compression error:', error);
    } finally {
      setIsCompressing(false);
    }
  };

  const loadCustomers = async () => {
    try {
      setLoading(true);
      const data = await customerApi.getCustomers();
      setCustomers(data);
    } catch (error) {
      console.error('Error loading customers:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddCustomer = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('full_name', newCustomer.full_name);
    if (newCustomer.email) formData.append('email', newCustomer.email);
    if (newCustomer.dob) formData.append('dob', new Date(newCustomer.dob).toISOString());
    if (newCustomer.photo) {
      formData.append('photo', newCustomer.photo);
    }

    try {
      await customerApi.createCustomer(formData);
      setShowAddModal(false);
      setNewCustomer({ full_name: '', email: '', dob: '', photo: null });
      loadCustomers();
    } catch (error) {
      console.error('Error creating customer:', error);
      alert('Erreur lors de la création du client');
    }
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
          <h1 className="text-lg font-bold tracking-tight text-primary dark:text-white">Clients</h1>
        </div>
        <button 
          onClick={() => setShowAddModal(true)}
          className="p-2 bg-primary/10 dark:bg-accent-blue/20 rounded-full text-primary dark:text-accent-blue"
        >
          <span className="material-icons-round">person_add</span>
        </button>
      </nav>

      <main className="p-4 max-w-md mx-auto space-y-4">
        {loading ? (
          <div className="text-center py-10 text-slate-500 font-medium">Chargement...</div>
        ) : customers.length === 0 ? (
          <div className="text-center py-20 space-y-4">
            <div className="w-20 h-20 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mx-auto text-slate-300 dark:text-slate-600">
              <span className="material-icons-round text-5xl">people_outline</span>
            </div>
            <p className="text-slate-500 font-medium text-sm">Aucun client trouvé</p>
            <button 
              onClick={() => setShowAddModal(true)}
              className="px-6 py-3 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold text-sm shadow-lg shadow-primary/20"
            >
              Ajouter un Client
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3" ref={listRef}>
            {customers.map((customer) => (
              <div 
                key={customer.id}
                onClick={() => navigate(`/customer/${customer.id}`)}
                className="bg-white dark:bg-slate-800 p-4 rounded-3xl border border-slate-200 dark:border-slate-700 shadow-sm flex items-center gap-4 active:scale-[0.98] transition-all cursor-pointer"
              >
                <div className="h-14 w-14 rounded-2xl bg-primary/5 overflow-hidden flex items-center justify-center border border-slate-100 dark:border-slate-700 shadow-inner">
                  {customer.photo_url ? (
                    <img src={getFileUrl(customer.photo_url)} alt={customer.full_name} className="h-full w-full object-cover" />
                  ) : (
                    <span className="material-icons-round text-3xl text-primary/30 dark:text-accent-blue/30">person</span>
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-slate-900 dark:text-white">{customer.full_name}</h3>
                  <p className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-widest mt-0.5">
                    Client ID: {customer.id.slice(0, 8)}
                  </p>
                </div>
                <span className="material-icons-round text-slate-300 dark:text-slate-600">chevron_right</span>
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
              <h2 className="text-2xl font-black text-slate-900 dark:text-white">Nouveau Client</h2>
              <button onClick={() => setShowAddModal(false)} className="p-2 bg-slate-100 dark:bg-slate-700 rounded-full text-slate-500">
                <span className="material-icons-round">close</span>
              </button>
            </div>

            <form onSubmit={handleAddCustomer} className="space-y-6">
              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">Nom Complet</label>
                <input
                  type="text"
                  required
                  value={newCustomer.full_name}
                  onChange={(e) => setNewCustomer({ ...newCustomer, full_name: e.target.value })}
                  className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl outline-none focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue text-sm"
                  placeholder="Jean Dupont"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">Email</label>
                  <input
                    type="email"
                    value={newCustomer.email}
                    onChange={(e) => setNewCustomer({ ...newCustomer, email: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl outline-none focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue text-sm"
                    placeholder="jean@example.com"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">Date de Naissance</label>
                  <input
                    type="date"
                    value={newCustomer.dob}
                    onChange={(e) => setNewCustomer({ ...newCustomer, dob: e.target.value })}
                    className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-2xl outline-none focus:ring-2 focus:ring-primary dark:focus:ring-accent-blue text-sm"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] font-bold uppercase text-slate-400 ml-1">Photo de Profil (Optionnel)</label>
                <div className="relative">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handlePhotoChange}
                    className="hidden"
                    id="photo-upload"
                  />
                  <label 
                    htmlFor="photo-upload"
                    className="w-full px-4 py-10 bg-slate-50 dark:bg-slate-900 border-2 border-dashed border-slate-200 dark:border-slate-700 rounded-3xl flex flex-col items-center justify-center gap-2 cursor-pointer hover:border-primary transition-colors relative"
                  >
                    {isCompressing ? (
                      <div className="flex flex-col items-center gap-2">
                        <div className="w-6 h-6 border-2 border-primary/30 border-t-primary rounded-full animate-spin"></div>
                        <span className="text-[10px] font-bold text-primary">Compression...</span>
                      </div>
                    ) : (
                      <>
                        <span className="material-icons-round text-3xl text-slate-300">add_a_photo</span>
                        <span className="text-xs font-bold text-slate-400 text-center">
                          {newCustomer.photo ? (
                            <span className="text-emerald-500">Photo sélectionnée ({Math.round(newCustomer.photo.size / 1024)} KB)</span>
                          ) : "Cliquez pour uploader"}
                        </span>
                      </>
                    )}
                  </label>
                </div>
              </div>

              <button
                type="submit"
                disabled={isCompressing}
                className="w-full py-4 bg-primary dark:bg-accent-blue text-white rounded-2xl font-bold shadow-lg shadow-primary/20 active:scale-95 transition-all disabled:opacity-50"
              >
                Créer le Client
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
        <button onClick={() => navigate('/customers')} className="flex flex-col items-center gap-1 text-primary dark:text-accent-blue">
          <span className="material-icons-round">groups</span>
          <span className="text-[10px] font-bold">Patients</span>
        </button>
        <button className="flex flex-col items-center gap-1 text-slate-400">
          <span className="material-icons-round">settings</span>
          <span className="text-[10px] font-medium">Réglages</span>
        </button>
      </footer>
    </div>
  );
};

export default CustomerList;

