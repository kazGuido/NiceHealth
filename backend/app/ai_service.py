import httpx
import os
import json
import logging
from typing import Dict, Any, Optional, AsyncIterator

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL   = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

# ---------------------------------------------------------------------------
# Field legend for X10 / X18_5 body-composition kiosk data
# This is injected into the AI prompt so the model knows every field exactly.
# ---------------------------------------------------------------------------
FIELD_LEGEND = """
=== LÉGENDE COMPLÈTE DES CHAMPS (appareils X10 / X18_5) ===

--- Enveloppe appareil (niveau supérieur) ---
deviceModel : modèle de l'appareil  (ex. "X10", "X18_5")
unitName    : nom de l'unité / point de mesure
unitNo      : numéro de l'unité
macAddr     : adresse MAC de l'appareil
deviceNo    : numéro de série de l'appareil (= deviceID du webhook)

--- Informations session ---
recordNo    : identifiant unique de la mesure (ex. "20260210134016")
measureTime : date et heure de la mesure (format "AAAA-MM-JJ HH:MM:SS")
userID      : identifiant utilisateur sur l'appareil
loginType   : type de connexion (0 = manuel / anonyme)
address     : champ adresse libre (souvent vide)

--- Informations patient ---
name        : prénom / nom du patient (entré sur le kiosque)
age         : âge en années
sex         : sexe  → 1 = Homme, 2 = Femme  (attention : PAS 0/1)
birthday    : date de naissance (souvent vide)

--- Mesures physiques de base ---
height      : taille en cm
weight      : poids en kg

--- Indice de Masse Corporelle (IMC) ---
bmi         : valeur IMC calculée par l'appareil
bmi_n       : plage normale de l'IMC pour ce profil (ex. "18.5-24.9")
bmiType     : code statut IMC → 0=Sous-poids, 1=Normal, 2=Surpoids, 3=Obésité, 4=Obésité sévère
bmi_s       : code statut IMC numérique → 0=Faible, 1=Normal, 2=Élevé
weight_n    : plage de poids idéal pour ce profil (ex. "52.1 - 70.3 kg")
weight_s    : statut poids → 0=Faible, 1=Normal, 2=Élevé
weAdjus     : ajustement de poids recommandé en kg (négatif = doit perdre du poids)
bodyScore   : score global de composition corporelle sur 100 (plus élevé = meilleur)
bodyAge     : âge corporel estimé par l'appareil en années

--- Masse grasse ---
fatRate       : taux de masse grasse en %
fatRate_n     : plage normale du taux de masse grasse pour ce profil (ex. "21 - 28")
fatRate_s     : statut → 0=Faible, 1=Normal, 2=Élevé
fatFree       : masse maigre (sans graisse) en kg
fatFree_n     : plage normale de masse maigre
fatFree_s     : statut masse maigre
fatSubCutRate : taux de graisse sous-cutanée en %
fatSubCutRate_n : plage normale
fatSubCutRate_s : statut
faAdjus       : ajustement masse grasse recommandé en kg (négatif = doit réduire)

--- Masse musculaire ---
muscleRate   : taux de masse musculaire en %
muscleRate_n : plage normale (ex. "46.9 - 55.9")
muscleRate_s : statut → 0=Faible, 1=Normal, 2=Élevé
muAdjus      : ajustement musculaire recommandé en kg (négatif = insuffisant)

--- Hydratation / eau corporelle ---
waterRate    : taux d'eau corporelle totale en %
waterRate_n  : plage normale (ex. "54.9 - 65.0")
waterRate_s  : statut
waterECW     : eau extracellulaire en litres
waterECW_n   : plage normale
waterECW_s   : statut
waterICW     : eau intracellulaire en litres
waterICW_n   : plage normale
waterICW_s   : statut

--- Os et minéraux ---
bone      : masse osseuse en kg
bone_n    : plage normale (ex. "3.1 - 3.3")
bone_s    : statut → 0=Faible, 1=Normal, 2=Élevé
mineral   : teneur en minéraux en kg
mineral_n : plage normale
mineral_s : statut

--- Protéines ---
protein   : taux de protéines en %
protein_n : plage normale (ex. "16.3 - 18.4")
protein_s : statut

--- Métabolisme de base ---
bmr   : métabolisme basal (BMR) en kcal/jour
bmr_n : valeur normale minimale (ex. "≥1967")
bmr_s : statut → 0=Insuffisant, 1=Normal, 2=Élevé

--- Graisse viscérale ---
vfal   : niveau de graisse viscérale (indice appareil)
vfal_n : plage normale (ex. "0.0 - 9.0")
vfal_s : statut → 0=Faible, 1=Normal, 2=Élevé

--- Pression artérielle (bras gauche / principal) ---
sbp   : pression systolique en mmHg
sbp_n : plage normale (ex. "90 - 139")
sbp_s : statut → 0=Faible, 1=Normal, 2=Élevé
dbp   : pression diastolique en mmHg
dbp_n : plage normale (ex. "60 - 89")
dbp_s : statut

--- Pression artérielle (bras droit, certains modèles X10) ---
sbpR / sbpR_n / sbpR_s  : idem bras gauche, bras droit
dbpR / dbpR_n / dbpR_s  : idem

--- Fréquence cardiaque ---
hr   : fréquence cardiaque en bpm
hr_n : plage normale (ex. "60 - 100")
hr_s : statut
hrR  : fréquence cardiaque bras droit (certains modèles)
hrR_n / hrR_s : idem

=== CODES STATUT (_s) ===
0 = En dessous de la normale (Faible / Insuffisant)
1 = Dans la normale
2 = Au-dessus de la normale (Élevé / Excessif)
3 = Très élevé / Critique

=== CODES bmiType ===
0 = Sous-poids   1 = Normal   2 = Surpoids   3 = Obésité   4 = Obésité sévère

=== CODES sex ===
1 = Homme   2 = Femme   (NE PAS INVERSER)
""".strip()


def _resolve_primary_record(payload: Dict[str, Any]):
    """
    Returns (device_context, record) where record is the first element of
    datas/tbDatas, or the flat payload itself.
    device_context contains the top-level wrapper fields (model, mac, etc.).
    """
    device_fields = ('deviceModel', 'unitName', 'unitNo', 'macAddr', 'deviceNo')
    device_context = {k: payload[k] for k in device_fields if k in payload}

    for key in ('datas', 'tbDatas'):
        arr = payload.get(key)
        if isinstance(arr, list) and len(arr) > 0:
            return device_context, arr[0]

    # Flat format (legacy / X18_5 minimal)
    return {}, payload


def _sex_label(raw_sex) -> Optional[str]:
    """Convert raw sex field to human-readable label.
    X10/X18_5: 1=Homme, 2=Femme   |   Legacy: 0=Femme, 1=Homme
    """
    if raw_sex is None:
        return None
    s = str(raw_sex).strip()
    if s == '1':   return 'Homme'
    if s == '2':   return 'Femme'   # X10/X18_5
    if s == '0':   return 'Femme'   # legacy encoding
    return None


async def analyze_health_data(
    measurement_data: Dict[str, Any],
    customer_info:    Optional[Dict[str, Any]] = None,
    device_context:   Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyse les données de santé via OpenRouter LLM.
    Sortie structurée en JSON, entièrement en français.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_api_key_here":
        return {
            "error": "OpenRouter API key not configured",
            "summary": "L'analyse IA n'est pas disponible.",
            "interpretation": "Veuillez configurer OPENROUTER_API_KEY dans l'environnement.",
            "recommendations": []
        }

    # ------------------------------------------------------------------
    # 1. Resolve the primary data record
    # ------------------------------------------------------------------
    dev_ctx, record = _resolve_primary_record(measurement_data)
    # Merge any externally-passed device_context on top
    if device_context:
        dev_ctx.update(device_context)

    # ------------------------------------------------------------------
    # 2. Build an enriched copy of the record for the model:
    #    - Add human-readable sex label
    #    - Add computed status labels next to each _s field
    # ------------------------------------------------------------------
    STATUS_MAP = {'0': 'Faible/Insuffisant', '1': 'Normal', '2': 'Élevé', '3': 'Très élevé/Critique'}
    BMI_TYPE_MAP = {'0': 'Sous-poids', '1': 'Normal', '2': 'Surpoids', '3': 'Obésité', '4': 'Obésité sévère'}

    enriched = dict(record)

    # Sex
    raw_sex = enriched.get('sex')
    if raw_sex is not None:
        enriched['sex_label'] = _sex_label(raw_sex) or str(raw_sex)

    # bmiType
    bmi_type = enriched.get('bmiType')
    if bmi_type is not None:
        enriched['bmiType_label'] = BMI_TYPE_MAP.get(str(bmi_type), f'Type {bmi_type}')

    # All _s fields → add _label sibling
    for key, val in list(enriched.items()):
        if key.endswith('_s') and val is not None:
            enriched[f'{key}_label'] = STATUS_MAP.get(str(val), str(val))

    # ------------------------------------------------------------------
    # 3. Build prompt sections
    # ------------------------------------------------------------------
    sections = []

    if dev_ctx:
        sections.append(f"APPAREIL:\n{json.dumps(dev_ctx, ensure_ascii=False, indent=2)}")

    if customer_info:
        sections.append(f"INFORMATIONS CLIENT:\n{json.dumps(customer_info, ensure_ascii=False, indent=2)}")

    sections.append(f"DONNÉES DE MESURE:\n{json.dumps(enriched, ensure_ascii=False, indent=2)}")

    data_block = "\n\n".join(sections)

    # ------------------------------------------------------------------
    # 4. Full prompt
    # ------------------------------------------------------------------
    prompt = f"""
{FIELD_LEGEND}

---

Tu es un professionnel de santé expert en composition corporelle et en bilans de kiosque santé.
Analyse les données ci-dessous et produis un compte rendu complet, personnalisé et bienveillant EN FRANÇAIS.

{data_block}

---

INSTRUCTIONS D'ANALYSE :

1. IDENTIFICATION DU PROFIL : utilise name, age, sex_label, height, weight pour personnaliser.
2. SCORE GLOBAL : si bodyScore est présent, commente-le (ex. > 80 = très bien).
3. ÂGE CORPOREL : si bodyAge est présent, compare-le à l'âge réel et explique ce que cela signifie.
4. IMC : interprète bmi par rapport à bmi_n et bmiType_label. Mentionne weAdjus pour indiquer l'objectif poids concret.
5. COMPOSITION CORPORELLE (si disponible) :
   - Masse grasse (fatRate) : compare à fatRate_n, utilise fatRate_s_label, mentionne faAdjus.
   - Graisse sous-cutanée (fatSubCutRate) : interprète fatSubCutRate_s_label.
   - Masse maigre / Masse musculaire (muscleRate, fatFree) : interprète par rapport aux normes.
   - Hydratation (waterRate, waterECW, waterICW) : interprète le ratio ECW/ICW si disponible.
   - Os (bone), Minéraux (mineral), Protéines (protein) : signale toute anomalie.
6. MÉTABOLISME : bmr comparé à bmr_n. Explique ce que cela signifie pour l'alimentation.
7. GRAISSE VISCÉRALE : vfal comparé à vfal_n. Souligne l'importance si élevé (risque cardiovasculaire).
8. CARDIOVASCULAIRE (si disponible) : sbp/dbp par rapport à sbp_n/dbp_n. Fréquence cardiaque hr vs hr_n.
   Si sbpR/dbpR présents (bras droit), comparer les deux bras.
9. CONSEILS : 4 à 6 conseils concrets, actionnables, adaptés au sexe, à l'âge et aux anomalies détectées.
   Format: objet avec "domaine" (ex. "Alimentation"), "conseil" (texte), "priorite" ("haute"/"moyenne"/"faible").

Réponds UNIQUEMENT avec un objet JSON valide contenant ces clés exactes :

{{
  "summary": "Résumé global en 2-3 phrases : état général, IMC, score corporel, point fort et point d'attention principal.",
  "body_age_comment": "Commentaire sur l'âge corporel vs âge réel (null si bodyAge absent).",
  "sections": {{
    "imc_poids": "Interprétation IMC et poids (2-4 phrases).",
    "composition_graisses": "Masse grasse, graisse sous-cutanée, graisse viscérale (si données disponibles, sinon null).",
    "composition_muscle_eau": "Masse musculaire, hydratation, masse osseuse, protéines (si données disponibles, sinon null).",
    "metabolisme": "BMR et implications nutritionnelles (si disponible, sinon null).",
    "cardiovasculaire": "Tension artérielle, fréquence cardiaque (si disponibles, sinon null)."
  }},
  "anomalies": ["Liste des valeurs hors norme (_s = 0 ou 2/3), formulées simplement pour le patient."],
  "recommendations": [
    {{
      "domaine": "Alimentation",
      "conseil": "...",
      "priorite": "haute"
    }}
  ],
  "disclaimer": "Ce bilan est indicatif. Consultez un professionnel de santé pour un avis médical."
}}

Tout le texte doit être en français uniquement, sans aucun mélange avec l'anglais ni d'autres langues (hors unités comme kg, %, mmHg). Ton professionnel, encourageant et accessible. Ne pas inventer de données absentes et ne pas mentionner explicitement les données manquantes (ne pas écrire que certaines valeurs sont absentes ou non fournies).
""".strip()

    # ------------------------------------------------------------------
    # 5. Call OpenRouter
    # ------------------------------------------------------------------
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization":  f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type":   "application/json",
                    "HTTP-Referer":   "https://niceq.nicedaytech.com",
                    "X-Title":        "NiceDay Health Kiosk",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Tu es un analyste expert en données de santé et composition corporelle. "
                                "Tu produis des comptes rendus précis, bienveillants et actionnables basés "
                                "sur les mesures de kiosques santé. Tu réponds TOUJOURS en français uniquement, "
                                "sans aucun mélange avec l'anglais ni d'autres langues (hors unités comme kg, %, mmHg). "
                                "Tu réponds TOUJOURS en JSON valide selon le schéma demandé."
                            )
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"}
                },
                timeout=45.0
            )

            response.raise_for_status()
            result = response.json()

            # OpenRouter can return error payload or empty choices (e.g. rate limit, model error)
            if result.get("error"):
                err = result["error"]
                msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                logger.warning(f"OpenRouter API error: {msg}")
                return {
                    "error": msg,
                    "summary": "Le service d'analyse n'a pas pu traiter la demande.",
                    "interpretation": msg,
                    "advice": ["Veuillez réessayer dans quelques instants."],
                    "recommendations": [],
                    "sections": {},
                    "anomalies": [],
                }

            choices = result.get("choices") or []
            if not choices or not isinstance(choices, list):
                logger.warning(f"OpenRouter unexpected response (no choices): keys={list(result.keys())}")
                return {
                    "error": "Réponse inattendue du service d'analyse.",
                    "summary": "L'analyse n'a pas pu être générée.",
                    "interpretation": "Le modèle n'a pas renvoyé de résultat. Essayez un autre modèle (OPENROUTER_MODEL) ou réessayez plus tard.",
                    "advice": ["Veuillez réessayer ultérieurement."],
                    "recommendations": [],
                    "sections": {},
                    "anomalies": [],
                }

            content = choices[0].get("message", {}).get("content") or ""
            if not content or not content.strip():
                logger.warning("OpenRouter returned empty content")
                return {
                    "error": "Réponse vide du service d'analyse.",
                    "summary": "Aucun texte d'analyse généré.",
                    "interpretation": "Le service n'a pas produit de contenu. Réessayez ou changez de modèle.",
                    "advice": ["Veuillez réessayer."],
                    "recommendations": [],
                    "sections": {},
                    "anomalies": [],
                }

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as je:
                logger.warning(f"OpenRouter returned non-JSON content: {content[:200]}... error={je}")
                return {
                    "error": "Le modèle n'a pas renvoyé de JSON valide.",
                    "summary": "Impossible de parser l'analyse.",
                    "interpretation": "Réponse du modèle invalide. Essayez un autre modèle (OPENROUTER_MODEL) compatible avec response_format json_object.",
                    "advice": ["Changez OPENROUTER_MODEL ou réessayez."],
                    "recommendations": [],
                    "sections": {},
                    "anomalies": [],
                }

            # ------------------------------------------------------------------
            # Back-compat: keep legacy keys (summary, interpretation, advice)
            # so existing frontend code still works while we roll out v2 fields.
            # ------------------------------------------------------------------
            if 'interpretation' not in parsed:
                parts = [v for v in [
                    parsed.get('sections', {}).get('imc_poids'),
                    parsed.get('sections', {}).get('composition_graisses'),
                    parsed.get('sections', {}).get('cardiovasculaire'),
                ] if v]
                parsed['interpretation'] = ' '.join(parts) if parts else parsed.get('summary', '')

            if 'advice' not in parsed:
                parsed['advice'] = [
                    r.get('conseil', str(r)) if isinstance(r, dict) else str(r)
                    for r in parsed.get('recommendations', [])
                ]

            return parsed

    except Exception as e:
        logger.error(f"Error calling OpenRouter: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "summary": "Échec de la génération de l'analyse IA.",
            "interpretation": "Une erreur s'est produite lors de la communication avec le service IA.",
            "advice": ["Veuillez réessayer ultérieurement."],
            "recommendations": [],
            "sections": {},
            "anomalies": [],
        }


def _build_stream_prompt(data_block: str) -> str:
    """Prompt for streaming: prose only (no JSON), so the user sees text appear naturally."""
    return f"""
{FIELD_LEGEND}

---

Tu es un professionnel de santé expert en composition corporelle et bilans de kiosque santé.
Analyse les données ci-dessous et rédige un compte rendu EN FRANÇAIS UNIQUEMENT, en texte continu (pas de JSON), sans aucun mélange avec l'anglais ni d'autres langues (hors unités comme kg, %, mmHg).

{data_block}

---

Rédige un seul bloc de texte en français, avec :
1. Un résumé en 2-3 phrases (état général, IMC, score corporel, point fort et point d'attention).
2. Si pertinent : âge corporel vs âge réel, interprétation IMC et poids, composition (masse grasse, muscle, hydratation), métabolisme, graisse viscérale, tension/fréquence cardiaque si disponibles.
3. Points d'attention : valeurs hors norme formulées simplement.
4. Conseils personnalisés : 4 à 6 conseils concrets et actionnables.
5. En fin : "Ce bilan est indicatif. Consultez un professionnel de santé pour un avis médical."

Ton professionnel, encourageant et accessible. N'invente pas de données absentes et ne mentionne pas explicitement les données manquantes (ne pas écrire que certaines valeurs sont absentes ou non fournies).
""".strip()


async def stream_health_analysis(
    measurement_data: Dict[str, Any],
    customer_info: Optional[Dict[str, Any]] = None,
    device_context: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[str]:
    """
    Stream analysis as plain text (prose) for live display.
    Yields SSE-friendly text chunks. No JSON – so no parsing bugs and nice streaming UX.
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_api_key_here":
        yield json.dumps({"error": "OpenRouter API key not configured"})
        return

    dev_ctx, record = _resolve_primary_record(measurement_data)
    if device_context:
        dev_ctx.update(device_context)

    STATUS_MAP = {'0': 'Faible/Insuffisant', '1': 'Normal', '2': 'Élevé', '3': 'Très élevé/Critique'}
    BMI_TYPE_MAP = {'0': 'Sous-poids', '1': 'Normal', '2': 'Surpoids', '3': 'Obésité', '4': 'Obésité sévère'}
    enriched = dict(record)
    raw_sex = enriched.get('sex')
    if raw_sex is not None:
        enriched['sex_label'] = _sex_label(raw_sex) or str(raw_sex)
    bmi_type = enriched.get('bmiType')
    if bmi_type is not None:
        enriched['bmiType_label'] = BMI_TYPE_MAP.get(str(bmi_type), f'Type {bmi_type}')
    for key, val in list(enriched.items()):
        if key.endswith('_s') and val is not None:
            enriched[f'{key}_label'] = STATUS_MAP.get(str(val), str(val))

    sections = []
    if dev_ctx:
        sections.append(f"APPAREIL:\n{json.dumps(dev_ctx, ensure_ascii=False, indent=2)}")
    if customer_info:
        sections.append(f"INFORMATIONS CLIENT:\n{json.dumps(customer_info, ensure_ascii=False, indent=2)}")
    sections.append(f"DONNÉES DE MESURE:\n{json.dumps(enriched, ensure_ascii=False, indent=2)}")
    data_block = "\n\n".join(sections)
    prompt = _build_stream_prompt(data_block)

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://niceq.nicedaytech.com",
                    "X-Title": "NiceDay Health Kiosk",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Tu es un analyste expert en données de santé. "
                                "Tu rédiges des comptes rendus exclusivement en français, "
                                "en texte continu (pas de JSON), sans aucun mélange avec l'anglais "
                                "ni d'autres langues (hors unités comme kg, %, mmHg)."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True,
                },
                timeout=60.0,
            ) as response:
                response.raise_for_status()
                buffer = ""
                async for chunk in response.aiter_text():
                    buffer += chunk
                    while "\n" in buffer or "\r" in buffer:
                        line, buffer = (buffer.split("\n", 1) + [""])[0], (buffer.split("\n", 1) + ["", ""])[1]
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            return
                        try:
                            obj = json.loads(data)
                            choices = obj.get("choices") or []
                            if choices and isinstance(choices, list):
                                delta = choices[0].get("delta") or {}
                                content = delta.get("content") or ""
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error(f"Stream OpenRouter error: {str(e)}", exc_info=True)
        yield json.dumps({"error": str(e)})
