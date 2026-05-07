import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';

const V2Report = () => {
    const { id } = useParams();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002';

    useEffect(() => {
        const fetchReport = async () => {
            try {
                const response = await axios.get(`${API_URL}/v2/report/${id}`);
                setData(response.data);
                setLoading(false);
            } catch (err) {
                console.error("Error fetching v2 report:", err);
                setError("Could not find this health report.");
                setLoading(false);
            }
        };

        fetchReport();
    }, [id, API_URL]);

    if (loading) return (
        <div className="flex items-center justify-center min-h-screen">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
    );

    if (error) return (
        <div className="flex flex-col items-center justify-center min-h-screen px-4 text-center">
            <h1 className="text-2xl font-bold text-gray-800 mb-2">Oops!</h1>
            <p className="text-gray-600">{error}</p>
        </div>
    );

    const { measurement, customer, branding, analysis } = data;
    const themeColor = branding.primary_color;

    return (
        <div className="min-h-screen bg-gray-50 pb-12">
            {/* Header / Branding */}
            <header 
                className="bg-white shadow-sm sticky top-0 z-10"
                style={{ borderTop: `4px solid ${themeColor}` }}
            >
                <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
                    <div className="flex items-center space-x-3">
                        {branding.logo_url ? (
                            <img src={branding.logo_url} alt={branding.business_name} className="h-10 w-auto" />
                        ) : (
                            <div 
                                className="h-10 w-10 rounded-lg flex items-center justify-center text-white font-bold text-xl"
                                style={{ backgroundColor: themeColor }}
                            >
                                {branding.business_name.charAt(0)}
                            </div>
                        )}
                        <span className="font-bold text-xl text-gray-800">{branding.business_name}</span>
                    </div>
                    <div className="text-xs text-gray-500 hidden sm:block">
                        Rapport de santé confidentiel
                    </div>
                </div>
            </header>

            <main className="max-w-4xl mx-auto px-4 mt-8">
                {/* Intro Section */}
                <div className="bg-white rounded-2xl shadow-sm p-6 mb-6">
                    <div className="flex items-center space-x-4 mb-4">
                        {customer?.photo_url ? (
                            <img src={customer.photo_url} alt={customer.name} className="h-16 w-16 rounded-full object-cover border-2 border-gray-100" />
                        ) : (
                            <div className="h-16 w-16 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-2xl">
                                {customer?.name?.charAt(0) || '?'}
                            </div>
                        )}
                        <div>
                            <h2 className="text-2xl font-bold text-gray-900">Bonjour, {customer?.name || 'Client'}</h2>
                            <p className="text-gray-500">Mesures effectuées le {new Date(measurement.created_at).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
                        </div>
                    </div>
                </div>

                {/* Vitals Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                    {Object.entries(measurement.data).map(([key, value]) => {
                        // Simple normalization for display
                        if (typeof value === 'object' || Array.isArray(value)) return null;
                        return (
                            <div key={key} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                                <p className="text-gray-500 text-xs uppercase font-semibold mb-1">{key.replace('_', ' ')}</p>
                                <p className="text-2xl font-bold text-gray-900">{value}</p>
                            </div>
                        );
                    })}
                </div>

                {/* AI Analysis Section */}
                {analysis && !analysis.error && (
                    <div className="space-y-6">
                        <section className="bg-white rounded-2xl shadow-sm p-6 border-l-4" style={{ borderColor: themeColor }}>
                            <h3 className="text-lg font-bold text-gray-900 mb-3">Résumé de votre santé</h3>
                            <p className="text-gray-700 leading-relaxed">{analysis.summary}</p>
                        </section>

                        <section className="bg-white rounded-2xl shadow-sm p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-3">Interprétation</h3>
                            <p className="text-gray-700 leading-relaxed">{analysis.interpretation}</p>
                        </section>

                        <section className="bg-white rounded-2xl shadow-sm p-6">
                            <h3 className="text-lg font-bold text-gray-900 mb-3">Conseils personnalisés</h3>
                            <ul className="space-y-3">
                                {analysis.advice?.map((tip, index) => (
                                    <li key={index} className="flex items-start space-x-3">
                                        <span className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold" style={{ backgroundColor: themeColor }}>
                                            {index + 1}
                                        </span>
                                        <span className="text-gray-700">{tip}</span>
                                    </li>
                                ))}
                            </ul>
                        </section>
                    </div>
                )}

                {/* CTA Section */}
                <div className="mt-12 text-center">
                    <a 
                        href={branding.cta_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-block px-8 py-3 rounded-full text-white font-bold shadow-lg transition-transform hover:scale-105"
                        style={{ backgroundColor: themeColor }}
                    >
                        {branding.cta_text}
                    </a>
                    {!branding.is_premium && (
                        <p className="mt-4 text-xs text-gray-400">
                            Propulsé par NiceDay Technologies
                        </p>
                    )}
                </div>
            </main>
        </div>
    );
};

export default V2Report;

