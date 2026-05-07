import React from 'react';

/**
 * Dynamically renders fields from JSONB data
 * Recognizes common health metrics and renders them with special formatting
 */
export const DynamicField = ({ label, value, unit = '' }) => {
  if (value === null || value === undefined) return null;

  // Handle different value types
  if (typeof value === 'object' && !Array.isArray(value)) {
    // Recursive rendering for nested objects
    return (
      <div className="space-y-2">
        {Object.entries(value).map(([key, val]) => (
          <DynamicField key={key} label={key} value={val} />
        ))}
      </div>
    );
  }

  if (Array.isArray(value)) {
    return (
      <div>
        <p className="text-xs text-slate-400 mb-1">{label}</p>
        <ul className="list-disc list-inside text-sm">
          {value.map((item, idx) => (
            <li key={idx}>{String(item)}</li>
          ))}
        </ul>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-xs text-slate-400">{label}</p>
      <p className="text-lg font-semibold dark:text-white">
        {value} {unit && <span className="text-sm font-normal text-slate-500">{unit}</span>}
      </p>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Status / code decoders (shared)
// ---------------------------------------------------------------------------

/**
 * Generic _s status code → French label
 * Device encoding: 0 = Below normal, 1 = Normal, 2 = Above normal / High
 */
export const getStatusLabel = (s) => {
  if (s == null || s === '') return null;
  const map = { '0': 'Faible', '1': 'Normal', '2': 'Élevé', '3': 'Très élevé' };
  return map[String(s)] ?? null;
};

/**
 * bmiType code → French label
 * 0 = Underweight, 1 = Normal, 2 = Overweight, 3 = Obese, 4 = Severely Obese
 */
export const getBMITypeLabel = (bmiType) => {
  if (bmiType == null || bmiType === '') return null;
  const map = {
    '0': 'Sous-poids',
    '1': 'Normal',
    '2': 'Surpoids',
    '3': 'Obésité',
    '4': 'Obésité sévère',
  };
  return map[String(bmiType)] ?? `Type ${bmiType}`;
};

/**
 * sex field → French label
 * X10/X18 encoding: 1 = Male (Homme), 2 = Female (Femme)
 * Legacy encoding:  0 = Female,        1 = Male
 */
export const getSexLabel = (sex) => {
  if (sex == null || sex === '') return null;
  const s = String(sex);
  if (s === '1') return 'Homme';
  if (s === '2') return 'Femme';
  if (s === '0') return 'Femme'; // legacy
  return null;
};

// ---------------------------------------------------------------------------
// BMI helpers
// ---------------------------------------------------------------------------

export const getBMICategory = (bmi) => {
  if (!bmi) return { category: null, color: 'slate', label: 'N/A' };
  const v = parseFloat(bmi);
  if (v < 18.5) return { category: 'underweight', color: 'blue',  label: 'Sous-poids' };
  if (v < 25)   return { category: 'normal',      color: 'green', label: 'Normal' };
  if (v < 30)   return { category: 'overweight',  color: 'amber', label: 'Surpoids' };
  if (v < 35)   return { category: 'obesity',     color: 'rose',  label: 'Obésité' };
  return          { category: 'severe_obesity',    color: 'rose',  label: 'Obésité sévère' };
};

export const getBMIGaugePosition = (bmi) => {
  if (!bmi) return 0;
  const minBMI = 15, maxBMI = 40;
  return Math.max(0, Math.min(100, ((parseFloat(bmi) - minBMI) / (maxBMI - minBMI)) * 100));
};

// ---------------------------------------------------------------------------
// Main metric extractor
// ---------------------------------------------------------------------------

/**
 * Extract and normalise ALL known health metrics from a JSONB payload.
 *
 * Supported device formats:
 *   - X10 / X18_5 kiosk format  →  { deviceModel, unitName, unitNo, macAddr, deviceNo, datas: [{...}] }
 *   - Legacy flat format         →  { action, deviceID, ...fields }
 *   - Array wrapper              →  [ {...} ]
 *
 * Field names follow the X10/X18_5 naming convention documented below.
 */
export const extractHealthMetrics = (data) => {
  const metrics = {
    // --- Device / session ---
    deviceModel:  null,
    unitName:     null,
    unitNo:       null,
    macAddr:      null,
    deviceNo:     null,
    measureTime:  null,
    recordNo:     null,
    userID:       null,
    loginType:    null,
    address:      null,

    // --- Patient info ---
    userInfo: { name: null, age: null, sex: null, birthday: null },

    // --- Physical basics ---
    height: null,
    weight: null,
    bmi:    null,

    // --- BMI analysis ---
    bmiNorm:    null,   // bmi_n   e.g. "18.5-24.9"
    bmiType:    null,   // bmiType 0-4
    bmi_s:      null,   // bmi status
    weightNorm: null,   // weight_n
    weight_s:   null,
    weAdjus:    null,   // weight adjustment (kg, negative = needs to lose)
    bodyScore:  null,   // overall score 0-100
    bodyAge:    null,   // estimated body age

    // --- Body fat ---
    fatRate:        null,  // %
    fatRate_n:      null,
    fatRate_s:      null,
    fatFree:        null,  // fat-free mass kg
    fatFree_n:      null,
    fatFree_s:      null,
    fatSubCutRate:  null,  // subcutaneous fat %
    fatSubCutRate_n: null,
    fatSubCutRate_s: null,
    faAdjus:        null,  // fat adjustment needed

    // --- Muscle ---
    muscleRate:   null,  // %
    muscleRate_n: null,
    muscleRate_s: null,
    muAdjus:      null,  // muscle adjustment

    // --- Water / Hydration ---
    waterRate:    null,  // total body water %
    waterRate_n:  null,
    waterRate_s:  null,
    waterECW:     null,  // extracellular water L
    waterECW_n:   null,
    waterECW_s:   null,
    waterICW:     null,  // intracellular water L
    waterICW_n:   null,
    waterICW_s:   null,

    // --- Bone & Minerals ---
    bone:       null,  // bone mass kg
    bone_n:     null,
    bone_s:     null,
    mineral:    null,  // mineral kg
    mineral_n:  null,
    mineral_s:  null,

    // --- Protein ---
    protein:    null,  // %
    protein_n:  null,
    protein_s:  null,

    // --- Metabolism ---
    bmr:    null,  // basal metabolic rate kcal/day
    bmr_n:  null,
    bmr_s:  null,

    // --- Visceral fat ---
    vfal:   null,  // visceral fat area level
    vfal_n: null,
    vfal_s: null,

    // --- Blood pressure (left / main) ---
    sbp:    null,  // systolic mmHg
    sbp_n:  null,
    sbp_s:  null,
    dbp:    null,  // diastolic mmHg
    dbp_n:  null,
    dbp_s:  null,

    // --- Blood pressure (right arm, some X10 units) ---
    sbpR:   null,
    sbpR_n: null,
    sbpR_s: null,
    dbpR:   null,
    dbpR_n: null,
    dbpR_s: null,

    // --- Heart rate ---
    hr:    null,  // bpm
    hr_n:  null,
    hr_s:  null,
    hrR:   null,  // right-side bpm
    hrR_n: null,
    hrR_s: null,

    // --- Catch-all for unknown fields ---
    other: {},
  };

  if (!data) return metrics;

  // -------------------------------------------------------------------------
  // 1. Resolve source record
  //    Priority: datas[0] > tbDatas[0] > array[0] > flat object
  //    Also capture top-level device wrapper fields.
  // -------------------------------------------------------------------------
  let sourceData = null;

  if (data && typeof data === 'object' && !Array.isArray(data)) {
    // Grab top-level device metadata before drilling into datas
    metrics.deviceModel = data.deviceModel || null;
    metrics.unitName    = data.unitName    || null;
    metrics.unitNo      = data.unitNo      || null;
    metrics.macAddr     = data.macAddr     || null;
    metrics.deviceNo    = data.deviceNo    || null;

    const arr = Array.isArray(data.datas)   ? data.datas
              : Array.isArray(data.tbDatas) ? data.tbDatas
              : null;
    if (arr && arr.length > 0) {
      sourceData = arr[0];
    } else {
      sourceData = data; // flat format
    }
  } else if (Array.isArray(data) && data.length > 0) {
    sourceData = data[0];
  }

  if (!sourceData) return metrics;

  // -------------------------------------------------------------------------
  // 2. Normalise keys (lowercase) for case-insensitive lookup
  // -------------------------------------------------------------------------
  const n = {};
  Object.keys(sourceData).forEach(k => { n[k.toLowerCase()] = sourceData[k]; });

  // Helper: try multiple key aliases, return first match
  const pick = (...keys) => {
    for (const k of keys) {
      const v = n[k.toLowerCase()];
      if (v !== undefined && v !== null && v !== '') return v;
    }
    return null;
  };

  // -------------------------------------------------------------------------
  // 3. Patient info
  // -------------------------------------------------------------------------
  metrics.userInfo.name     = pick('name', 'nom');
  metrics.userInfo.age      = pick('age');
  metrics.userInfo.sex      = pick('sex');  // 1=Homme, 2=Femme (X10); 0=Femme, 1=Homme (legacy)
  metrics.userInfo.birthday = pick('birthday', 'birth');

  metrics.userID    = pick('userid');
  metrics.loginType = pick('logintype');
  metrics.address   = pick('address');

  // -------------------------------------------------------------------------
  // 4. Session / device info (may also appear inside datas record)
  // -------------------------------------------------------------------------
  metrics.measureTime = pick('measuretime', 'measureTime');
  metrics.recordNo    = pick('recordno', 'recordNo');
  if (!metrics.deviceModel) metrics.deviceModel = pick('devicemodel', 'deviceModel');
  if (!metrics.unitName)    metrics.unitName     = pick('unitname',    'unitName');
  if (!metrics.unitNo)      metrics.unitNo       = pick('unitno',      'unitNo');
  if (!metrics.macAddr)     metrics.macAddr      = pick('macaddr',     'macAddr');
  if (!metrics.deviceNo)    metrics.deviceNo     = pick('deviceno',    'deviceNo');

  // -------------------------------------------------------------------------
  // 5. Physical basics
  // -------------------------------------------------------------------------
  metrics.height = pick('height', 'taille', 'height_cm');
  metrics.weight = pick('weight', 'poids',  'weight_kg');
  metrics.bmi    = pick('bmi', 'imc', 'bmi_value');

  // -------------------------------------------------------------------------
  // 6. BMI analysis
  // -------------------------------------------------------------------------
  metrics.bmiNorm   = pick('bmi_n');
  metrics.bmiType   = pick('bmitype', 'bmiType');
  metrics.bmi_s     = pick('bmi_s');
  metrics.weightNorm = pick('weight_n');
  metrics.weight_s  = pick('weight_s');
  metrics.weAdjus   = pick('weadjus', 'weAdjus');
  metrics.bodyScore = pick('bodyscore', 'bodyScore');
  metrics.bodyAge   = pick('bodyage',   'bodyAge');

  // -------------------------------------------------------------------------
  // 7. Body fat
  // -------------------------------------------------------------------------
  metrics.fatRate        = pick('fatrate', 'body_fat', 'fat_percentage');
  metrics.fatRate_n      = pick('fatrate_n');
  metrics.fatRate_s      = pick('fatrate_s');
  metrics.fatFree        = pick('fatfree');
  metrics.fatFree_n      = pick('fatfree_n');
  metrics.fatFree_s      = pick('fatfree_s');
  metrics.fatSubCutRate  = pick('fatsubcutrate');
  metrics.fatSubCutRate_n = pick('fatsubcutrate_n');
  metrics.fatSubCutRate_s = pick('fatsubcutrate_s');
  metrics.faAdjus        = pick('faadjus', 'faAdjus');

  // -------------------------------------------------------------------------
  // 8. Muscle
  // -------------------------------------------------------------------------
  metrics.muscleRate   = pick('musclerate', 'muscle_mass');
  metrics.muscleRate_n = pick('musclerate_n');
  metrics.muscleRate_s = pick('musclerate_s');
  metrics.muAdjus      = pick('muadjus', 'muAdjus');

  // -------------------------------------------------------------------------
  // 9. Water / hydration
  // -------------------------------------------------------------------------
  metrics.waterRate   = pick('waterrate', 'hydration');
  metrics.waterRate_n = pick('waterrate_n');
  metrics.waterRate_s = pick('waterrate_s');
  metrics.waterECW    = pick('waterecw');
  metrics.waterECW_n  = pick('waterecw_n');
  metrics.waterECW_s  = pick('waterecw_s');
  metrics.waterICW    = pick('watericw');
  metrics.waterICW_n  = pick('watericw_n');
  metrics.waterICW_s  = pick('watericw_s');

  // -------------------------------------------------------------------------
  // 10. Bone & minerals
  // -------------------------------------------------------------------------
  metrics.bone      = pick('bone', 'bone_mass', 'bonemass');
  metrics.bone_n    = pick('bone_n');
  metrics.bone_s    = pick('bone_s');
  metrics.mineral   = pick('mineral');
  metrics.mineral_n = pick('mineral_n');
  metrics.mineral_s = pick('mineral_s');

  // -------------------------------------------------------------------------
  // 11. Protein
  // -------------------------------------------------------------------------
  metrics.protein   = pick('protein');
  metrics.protein_n = pick('protein_n');
  metrics.protein_s = pick('protein_s');

  // -------------------------------------------------------------------------
  // 12. Metabolism (BMR)
  // -------------------------------------------------------------------------
  metrics.bmr   = pick('bmr', 'metabolism');
  metrics.bmr_n = pick('bmr_n');
  metrics.bmr_s = pick('bmr_s');

  // -------------------------------------------------------------------------
  // 13. Visceral fat
  // -------------------------------------------------------------------------
  metrics.vfal   = pick('vfal', 'visceralfat', 'visceral_fat_level');
  metrics.vfal_n = pick('vfal_n');
  metrics.vfal_s = pick('vfal_s');

  // -------------------------------------------------------------------------
  // 14. Blood pressure (left / main)
  // -------------------------------------------------------------------------
  metrics.sbp   = pick('sbp');
  metrics.sbp_n = pick('sbp_n');
  metrics.sbp_s = pick('sbp_s');
  metrics.dbp   = pick('dbp');
  metrics.dbp_n = pick('dbp_n');
  metrics.dbp_s = pick('dbp_s');

  // Legacy blood pressure formats
  if (!metrics.sbp && !metrics.dbp) {
    const bp = pick('blood_pressure', 'pression_arterielle', 'bp', 'bp_data');
    if (bp) {
      const m = String(bp).match(/(\d+)\s*[/\-]\s*(\d+)/);
      if (m) { metrics.sbp = m[1]; metrics.dbp = m[2]; }
    }
    if (!metrics.sbp) metrics.sbp = pick('systolic');
    if (!metrics.dbp) metrics.dbp = pick('diastolic');
  }

  // -------------------------------------------------------------------------
  // 15. Blood pressure (right arm)
  // -------------------------------------------------------------------------
  metrics.sbpR   = pick('sbpr');
  metrics.sbpR_n = pick('sbpr_n');
  metrics.sbpR_s = pick('sbpr_s');
  metrics.dbpR   = pick('dbpr');
  metrics.dbpR_n = pick('dbpr_n');
  metrics.dbpR_s = pick('dbpr_s');

  // -------------------------------------------------------------------------
  // 16. Heart rate
  // -------------------------------------------------------------------------
  metrics.hr    = pick('hr', 'heart_rate', 'pulse', 'frequence_cardiaque');
  metrics.hr_n  = pick('hr_n');
  metrics.hr_s  = pick('hr_s');
  metrics.hrR   = pick('hrr');
  metrics.hrR_n = pick('hrr_n');
  metrics.hrR_s = pick('hrr_s');

  // -------------------------------------------------------------------------
  // 17. Legacy / generic fields
  // -------------------------------------------------------------------------
  if (!metrics.userInfo.name) metrics.userInfo.name = pick('patient_name', 'patient');

  // -------------------------------------------------------------------------
  // 18. Calculate BMI from height + weight if missing
  // -------------------------------------------------------------------------
  if (!metrics.bmi && metrics.height && metrics.weight) {
    const h = parseFloat(metrics.height) / 100;
    const w = parseFloat(metrics.weight);
    if (h > 0 && w > 0) metrics.bmi = (w / (h * h)).toFixed(1);
  }

  // -------------------------------------------------------------------------
  // 19. Collect any remaining unknown fields into `other`
  // -------------------------------------------------------------------------
  const knownKeys = new Set([
    'name','nom','age','sex','birthday','birth','userid','logintype','address',
    'measuretime','recordno','devicemodel','unitname','unitno','macaddr','deviceno',
    'height','taille','height_cm','weight','poids','weight_kg',
    'bmi','imc','bmi_value','bmi_n','bmitype','bmi_s','weight_n','weight_s',
    'weadjus','bodyscore','bodyage',
    'fatrate','body_fat','fat_percentage','fatrate_n','fatrate_s',
    'fatfree','fatfree_n','fatfree_s',
    'fatsubcutrate','fatsubcutrate_n','fatsubcutrate_s','faadjus',
    'musclerate','muscle_mass','musclerate_n','musclerate_s','muadjus',
    'waterrate','hydration','waterrate_n','waterrate_s',
    'waterecw','waterecw_n','waterecw_s',
    'watericw','watericw_n','watericw_s',
    'bone','bone_mass','bonemass','bone_n','bone_s',
    'mineral','mineral_n','mineral_s',
    'protein','protein_n','protein_s',
    'bmr','metabolism','bmr_n','bmr_s',
    'vfal','visceralfat','visceral_fat_level','vfal_n','vfal_s',
    'sbp','sbp_n','sbp_s','dbp','dbp_n','dbp_s',
    'blood_pressure','pression_arterielle','bp','bp_data','systolic','diastolic',
    'sbpr','sbpr_n','sbpr_s','dbpr','dbpr_n','dbpr_s',
    'hr','heart_rate','pulse','frequence_cardiaque','hr_n','hr_s',
    'hrr','hrr_n','hrr_s',
    'patient_name','patient',
    // top-level wrapper keys (not in sourceData, but guard anyway)
    'datas','tbdatas',
  ]);

  Object.keys(sourceData).forEach(key => {
    if (!knownKeys.has(key.toLowerCase())) {
      metrics.other[key] = sourceData[key];
    }
  });

  return metrics;
};
