"""
Readers: load each raw source WITHOUT modifying it and map source field names
onto the common field names of config.SCHEMA. Values are left exactly as read
(strings, JSON numbers/booleans, or None for an absent XML element / JSON key).

Every staged record carries metadata keys that start with '_':
    _source  A/B/C/D
    _entity  target entity name
    _loc     where the record came from (file + line / XML path / JSON path)
    _raw     the original record as read, kept for the quarantine output

Structurally malformed rows (wrong field count) cannot be mapped to columns
reliably, so they are returned separately as rejects.
"""

import csv
import json
import xml.etree.ElementTree as ET

from config import RAW

# ---------------------------------------------------------------------------
# Source A - pipe-delimited TXT
# ---------------------------------------------------------------------------

A_FILES = {
    "professionals": ("professionals.txt", {"prof_no": "professional_id", "nom_complet": "full_name", "fonction": "role"}),
    "icd9_codes": ("icd9_dictionary.txt", {"code_cim9": "icd9_code", "libelle_officiel": "title", "categorie": "category"}),
    "patients": ("patients.txt", {"pat_no": "patient_id", "nom": "family_name", "prenom": "given_name",
                                  "date_naissance": "birth_date", "sexe": "sex", "adresse": "address",
                                  "telephone": "phone", "contact_urgence": "emergency_contact",
                                  "statut_vital": "life_status"}),
    "admissions": ("admissions.txt", {"sejour_no": "admission_id", "pat_no": "patient_id",
                                      "medecin_admission": "admitting_professional_id", "date_entree": "admit_time_utc",
                                      "type_sejour": "admission_type", "motif": "reason", "provenance": "arrival_mode",
                                      "assurance": "insurance", "date_sortie": "discharge_time_utc", "statut": "status"}),
    "triage": ("triage.txt", {"triage_no": "triage_id", "sejour_no": "admission_id", "infirmier": "nurse_id",
                              "date_heure": "assessed_at_utc", "tension": "blood_pressure", "fc": "heart_rate_bpm",
                              "fr": "resp_rate_per_min", "temp_c": "temperature_c", "spo2_pct": "spo2_pct",
                              "douleur": "pain_score", "symptomes": "symptoms", "allergies": "allergies",
                              "traitement": "home_medications", "priorite": "priority"}),
    "unit_stays": ("mouvements.txt", {"mvt_no": "stay_id", "sejour_no": "admission_id",
                                      "medecin_resp": "responsible_professional_id", "unite": "unit_type",
                                      "chambre": "room", "lit": "bed", "entree": "entry_time_utc",
                                      "sortie": "exit_time_utc", "motif_transfert": "transfer_reason"}),
    "diagnoses": ("diagnostics.txt", {"diag_no": "diagnosis_id", "pat_no": "patient_id", "sejour_no": "admission_id",
                                      "code_cim9": "icd9_code", "medecin": "professional_id",
                                      "date_heure": "diagnosed_at_utc", "rang": "rank"}),
    "orders": ("demandes_examen.txt", {"demande_no": "order_id", "sejour_no": "admission_id",
                                       "prescripteur": "requester_id", "date_heure": "ordered_at_utc",
                                       "examen": "exam", "motif": "indication", "statut": "status",
                                       "priorite": "priority"}),
    "radiology": ("radiologie.txt", {"examen_no": "exam_id", "sejour_no": "admission_id", "demande_no": "order_id",
                                     "medecin_ref": "referrer_id", "manipulateur": "technician_id",
                                     "type_examen": "exam_type", "date_heure": "performed_at_utc",
                                     "zone": "body_area", "statut": "status", "lien_images": "image_link",
                                     "compte_rendu": "findings"}),
    "procedures": ("chirurgie.txt", {"acte_no": "procedure_id", "sejour_no": "admission_id",
                                     "chirurgien": "surgeon_id", "intervention": "procedure",
                                     "date_heure": "performed_at_utc", "resultat": "outcome"}),
    "notes": ("notes_cliniques.txt", {"note_no": "note_id", "sejour_no": "admission_id", "auteur": "author_id",
                                      "type_note": "note_type", "date_heure": "written_at_utc", "contenu": "text"}),
    "discharges": ("sorties.txt", {"sortie_no": "discharge_id", "sejour_no": "admission_id",
                                   "medecin_autorisant": "authorizer_id", "date_sortie": "discharge_time_utc",
                                   "destination": "destination", "etat_sortie": "condition",
                                   "ordonnance": "prescriptions", "consignes": "instructions",
                                   "rdv": "follow_up_date"}),
}

# ---------------------------------------------------------------------------
# Source B - CSV
# ---------------------------------------------------------------------------

B_FILES = {
    "professionals": ("professionals.csv", {"ProviderID": "professional_id", "ProviderName": "full_name", "Title": "role"}),
    "icd9_codes": ("icd9_codes.csv", {"ICD9Code": "icd9_code", "Title": "title", "Chapter": "category"}),
    "patients": ("patients.csv", {"PatientID": "patient_id", "FullName": "_full_name", "DOB": "birth_date",
                                  "Sex": "sex", "HomeAddress": "address", "Phone": "phone",
                                  "EmergencyContact": "emergency_contact", "Deceased": "life_status"}),
    "admissions": ("encounters.csv", {"EncounterID": "admission_id", "PatientID": "patient_id",
                                      "AdmittingProviderID": "admitting_professional_id",
                                      "AdmitDateTime": "admit_time_utc", "AdmitType": "admission_type",
                                      "ChiefComplaint": "reason", "AdmitSource": "arrival_mode",
                                      "Insurance": "insurance", "DischargeDateTime": "discharge_time_utc",
                                      "EncounterStatus": "status"}),
    "triage": ("triage.csv", {"TriageID": "triage_id", "EncounterID": "admission_id", "NurseID": "nurse_id",
                              "AssessedAt": "assessed_at_utc", "BloodPressure": "blood_pressure",
                              "HeartRate": "heart_rate_bpm", "RespRate": "resp_rate_per_min",
                              "TempF": "temperature_c", "SpO2": "spo2_pct", "PainScore": "pain_score",
                              "Symptoms": "symptoms", "Allergies": "allergies", "HomeMeds": "home_medications",
                              "Acuity": "priority"}),
    "unit_stays": ("unit_stays.csv", {"StayID": "stay_id", "EncounterID": "admission_id",
                                      "AttendingID": "responsible_professional_id", "Unit": "unit_type",
                                      "Room": "room", "Bed": "bed", "InTime": "entry_time_utc",
                                      "OutTime": "exit_time_utc", "TransferReason": "transfer_reason"}),
    "diagnoses": ("diagnoses.csv", {"DxID": "diagnosis_id", "PatientID": "patient_id", "EncounterID": "admission_id",
                                    "ICD9": "icd9_code", "ProviderID": "professional_id",
                                    "DxDateTime": "diagnosed_at_utc", "DxRank": "rank"}),
    "orders": ("orders.csv", {"OrderID": "order_id", "EncounterID": "admission_id",
                              "OrderingProviderID": "requester_id", "OrderedAt": "ordered_at_utc", "Test": "exam",
                              "Indication": "indication", "OrderStatus": "status", "Priority": "priority"}),
    "radiology": ("imaging.csv", {"ImagingID": "exam_id", "EncounterID": "admission_id", "OrderID": "order_id",
                                  "ReferringProviderID": "referrer_id", "TechID": "technician_id",
                                  "Modality": "exam_type", "PerformedAt": "performed_at_utc", "BodyPart": "body_area",
                                  "Status": "status", "ImageURL": "image_link", "Impression": "findings"}),
    "procedures": ("procedures.csv", {"ProcedureID": "procedure_id", "EncounterID": "admission_id",
                                      "SurgeonID": "surgeon_id", "Procedure": "procedure",
                                      "PerformedAt": "performed_at_utc", "Outcome": "outcome"}),
    "notes": ("notes.csv", {"NoteID": "note_id", "EncounterID": "admission_id", "AuthorID": "author_id",
                            "NoteType": "note_type", "WrittenAt": "written_at_utc", "NoteText": "text"}),
    "discharges": ("discharges.csv", {"DischargeID": "discharge_id", "EncounterID": "admission_id",
                                      "AuthorizingProviderID": "authorizer_id", "DischargedAt": "discharge_time_utc",
                                      "Disposition": "destination", "ConditionAtDischarge": "condition",
                                      "Prescriptions": "prescriptions", "Instructions": "instructions",
                                      "FollowUp": "follow_up_date"}),
}


def _rec(source, entity, loc, raw, mapping):
    r = {"_source": source, "_entity": entity, "_loc": loc, "_raw": dict(raw)}
    for src_field, tgt in mapping.items():
        r[tgt] = raw.get(src_field)
    return r


def _malformed(source, entity, loc, raw_line, first_field, reason):
    # The first field is the record's own id; it is kept so that children of
    # the malformed record are reported as cascade rejections, not orphans.
    rid = int(first_field) if first_field.strip().isdigit() else None
    return {"_source": source, "_entity": entity, "_loc": loc, "_raw": {"line": raw_line},
            "_id": rid, "_reasons": [reason]}


def read_source_a():
    base = RAW / "source_A_europe"
    out, rejects = {}, []
    for entity, (fname, mapping) in A_FILES.items():
        rows = []
        with open(base / fname, encoding="utf-8", newline="") as f:
            lines = f.read().split("\n")
        header = lines[0].split("|")
        for n, line in enumerate(lines[1:], start=2):
            if line == "":
                continue
            parts = line.split("|")
            loc = f"{fname}:line {n}"
            if len(parts) != len(header):
                rejects.append(_malformed("A", entity, loc, line, parts[0],
                                          f"malformed_line: {len(parts)} fields, expected {len(header)}"))
                continue
            rows.append(_rec("A", entity, loc, dict(zip(header, parts)), mapping))
        out[entity] = rows
    return out, rejects


def read_source_b():
    base = RAW / "source_B_north_america"
    out, rejects = {}, []
    for entity, (fname, mapping) in B_FILES.items():
        rows = []
        with open(base / fname, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            for n, parts in enumerate(reader, start=2):
                loc = f"{fname}:row {n}"
                if len(parts) != len(header):
                    rejects.append(_malformed("B", entity, loc, ",".join(parts), parts[0],
                                              f"malformed_line: {len(parts)} fields, expected {len(header)}"))
                    continue
                r = _rec("B", entity, loc, dict(zip(header, parts)), mapping)
                if entity == "patients":
                    # FullName is "Last, First": split on the first comma only.
                    full = r.pop("_full_name")
                    last, sep, first = full.partition(",")
                    if first.startswith(" "):
                        first = first[1:]  # the single separator space of ", "
                    r["family_name"], r["given_name"] = (last, first) if sep else (None, full)
                rows.append(r)
        out[entity] = rows
    return out, rejects


# ---------------------------------------------------------------------------
# Source C - XML
# ---------------------------------------------------------------------------

def _xml_fields(el):
    """Child-element text: absent element -> key absent; empty element -> ''."""
    d = dict(el.attrib)
    for ch in el:
        if len(ch) == 0:
            d[ch.tag] = ch.text if ch.text is not None else ""
    return d


def read_source_c():
    root = ET.parse(RAW / "source_C_asia" / "hospital_asia.xml").getroot()
    out = {e: [] for e in A_FILES}
    S = "C"

    for m in root.find("staff"):
        raw = _xml_fields(m)
        out["professionals"].append(_rec(S, "professionals", f"staff/member[@staffId={raw.get('staffId')}]", raw,
                                         {"staffId": "professional_id", "name": "full_name", "role": "role"}))
    for e in root.find("icd9Dictionary"):
        raw = _xml_fields(e)
        out["icd9_codes"].append(_rec(S, "icd9_codes", f"icd9Dictionary/entry[@code={raw.get('code')}]", raw,
                                      {"code": "icd9_code", "title": "title", "category": "category"}))
    for p in root.find("patients"):
        raw = _xml_fields(p)
        name = p.find("name")
        if name is not None:
            for ch in name:
                raw[f"name/{ch.tag}"] = ch.text if ch.text is not None else ""
        out["patients"].append(_rec(S, "patients", f"patients/patient[@patientNo={raw.get('patientNo')}]", raw, {
            "patientNo": "patient_id", "name/family": "family_name", "name/given": "given_name",
            "birthDate": "birth_date", "gender": "sex", "address": "address", "phone": "phone",
            "nextOfKin": "emergency_contact", "vitalStatus": "life_status"}))

    rad_map = {"id": "exam_id", "orderRef": "order_id", "type": "exam_type", "at": "performed_at_utc",
               "bodyArea": "body_area", "status": "status", "images": "image_link", "report": "findings",
               "referrer": "referrer_id", "technician": "technician_id"}

    for i, a in enumerate(root.find("admissions"), start=1):
        aid = a.get("admissionNo")
        loc = f"admissions/admission[{i}][@admissionNo={aid}]"
        raw = _xml_fields(a)
        # An <admission> with no patientRef and no fields is a container shell
        # for children whose parent admission does not exist - not a record.
        is_shell = "patientRef" not in a.attrib and len(raw) == 1
        if not is_shell:
            out["admissions"].append(_rec(S, "admissions", loc, raw, {
                "admissionNo": "admission_id", "patientRef": "patient_id", "admittingStaff": "admitting_professional_id",
                "admittedAt": "admit_time_utc", "category": "admission_type", "reason": "reason",
                "arrivalMode": "arrival_mode", "insurer": "insurance", "dischargedAt": "discharge_time_utc",
                "status": "status"}))

        def child(entity, el, mapping, extra=None):
            raw_c = _xml_fields(el)
            raw_c["admissionNo"] = aid
            raw_c.update(extra or {})
            mapping = dict(mapping, admissionNo="admission_id")
            out[entity].append(_rec(S, entity, f"{loc}/{el.tag}[@id={el.get('id')}]", raw_c, mapping))

        for el in a:
            if el.tag == "triage":
                child("triage", el, {"id": "triage_id", "nurse": "nurse_id", "at": "assessed_at_utc", "bp": "blood_pressure",
                                     "pulse": "heart_rate_bpm", "respiration": "resp_rate_per_min",
                                     "temperatureC": "temperature_c", "oxygenSaturation": "spo2_pct", "pain": "pain_score",
                                     "symptoms": "symptoms", "allergies": "allergies", "medications": "home_medications",
                                     "level": "priority"})
            elif el.tag == "unitStay":
                child("unit_stays", el, {"id": "stay_id", "unit": "unit_type", "room": "room", "bed": "bed",
                                         "in": "entry_time_utc", "out": "exit_time_utc",
                                         "doctor": "responsible_professional_id", "transferReason": "transfer_reason"})
            elif el.tag == "diagnosis":
                child("diagnoses", el, {"id": "diagnosis_id", "patientRef": "patient_id", "icd9": "icd9_code",
                                        "kind": "rank", "at": "diagnosed_at_utc", "doctor": "professional_id"})
            elif el.tag == "order":
                child("orders", el, {"id": "order_id", "test": "exam", "at": "ordered_at_utc", "reason": "indication",
                                     "status": "status", "priority": "priority", "doctor": "requester_id"})
                for rad in el.findall("radiologyExam"):  # nested -> order id comes from the parent
                    child("radiology", rad, rad_map, extra={"orderRef": el.get("id")})
            elif el.tag == "radiologyExam":  # stand-alone exam with an explicit orderRef
                child("radiology", el, rad_map)
            elif el.tag == "surgery":
                child("procedures", el, {"id": "procedure_id", "procedure": "procedure", "at": "performed_at_utc",
                                         "outcome": "outcome", "surgeon": "surgeon_id"})
            elif el.tag == "note":
                child("notes", el, {"id": "note_id", "type": "note_type", "at": "written_at_utc", "author": "author_id",
                                    "text": "text"})
            elif el.tag == "discharge":
                child("discharges", el, {"id": "discharge_id", "at": "discharge_time_utc", "destination": "destination",
                                         "condition": "condition", "medications": "prescriptions",
                                         "followUp": "instructions", "appointment": "follow_up_date",
                                         "authorizedBy": "authorizer_id"})
    return out, []


# ---------------------------------------------------------------------------
# Source D - JSON
# ---------------------------------------------------------------------------

def read_source_d():
    with open(RAW / "source_D_africa" / "hospital_africa.json", encoding="utf-8") as f:
        doc = json.load(f)
    out = {e: [] for e in A_FILES}
    S = "D"
    for i, p in enumerate(doc["practitioners"]):
        out["professionals"].append(_rec(S, "professionals", f"practitioners[{i}]", p, {
            "practitioner_id": "professional_id", "display_name": "full_name", "speciality": "role"}))
    for i, c in enumerate(doc["icd9_reference"]):
        out["icd9_codes"].append(_rec(S, "icd9_codes", f"icd9_reference[{i}]", c,
                                      {"icd9": "icd9_code", "label": "title", "group": "category"}))
    for i, p in enumerate(doc["patients"]):
        flat = {k: v for k, v in p.items() if k != "contact"}
        for k, v in (p.get("contact") or {}).items():
            flat[f"contact.{k}"] = v
        out["patients"].append(_rec(S, "patients", f"patients[{i}]", flat, {
            "mrn": "patient_id", "surname": "family_name", "first_names": "given_name", "birth_date": "birth_date",
            "sex": "sex", "contact.address": "address", "contact.phone": "phone",
            "contact.next_of_kin": "emergency_contact", "deceased": "life_status"}))

    child_maps = {
        "triage": ("triage", {"triage_id": "triage_id", "nurse": "nurse_id", "at": "assessed_at_utc", "bp": "blood_pressure",
                              "pulse": "heart_rate_bpm", "resp_rate": "resp_rate_per_min", "temp_c": "temperature_c",
                              "spo2": "spo2_pct", "pain_score": "pain_score", "complaints": "symptoms",
                              "allergies": "allergies", "current_meds": "home_medications", "category": "priority"}),
        "ward_movements": ("unit_stays", {"movement_id": "stay_id", "ward": "unit_type", "room": "room", "bed": "bed",
                                          "from": "entry_time_utc", "to": "exit_time_utc",
                                          "clinician": "responsible_professional_id", "why": "transfer_reason"}),
        "diagnoses": ("diagnoses", {"dx_id": "diagnosis_id", "patient_mrn": "patient_id", "icd9": "icd9_code",
                                    "primary": "rank", "at": "diagnosed_at_utc", "by": "professional_id"}),
        "investigations": ("orders", {"order_id": "order_id", "test": "exam", "requested_at": "ordered_at_utc",
                                      "requested_by": "requester_id", "indication": "indication", "state": "status",
                                      "urgency": "priority"}),
        "imaging": ("radiology", {"imaging_id": "exam_id", "order_id": "order_id", "modality": "exam_type",
                                  "at": "performed_at_utc", "region": "body_area", "state": "status",
                                  "pacs_link": "image_link", "report": "findings", "referred_by": "referrer_id",
                                  "radiographer": "technician_id"}),
        "theatre": ("procedures", {"procedure_id": "procedure_id", "procedure": "procedure", "at": "performed_at_utc",
                                   "surgeon": "surgeon_id", "result": "outcome"}),
        "notes": ("notes", {"note_id": "note_id", "kind": "note_type", "at": "written_at_utc", "author": "author_id",
                            "body": "text"}),
        "discharge": ("discharges", {"discharge_id": "discharge_id", "at": "discharge_time_utc", "to": "destination",
                                     "condition": "condition", "scripts": "prescriptions", "advice": "instructions",
                                     "next_visit": "follow_up_date", "authorised_by": "authorizer_id"}),
    }
    for i, enc in enumerate(doc["encounters"]):
        eid = enc.get("encounter_id")
        loc = f"encounters[{i}](encounter_id={eid})"
        # A shell (no encounter fields, null patient) only holds orphan children.
        is_shell = enc.get("patient_mrn") is None and "encounter_type" not in enc
        if not is_shell:
            flat = {k: v for k, v in enc.items() if k not in child_maps}
            out["admissions"].append(_rec(S, "admissions", loc, flat, {
                "encounter_id": "admission_id", "patient_mrn": "patient_id", "admitted_by": "admitting_professional_id",
                "start": "admit_time_utc", "encounter_type": "admission_type", "reason": "reason",
                "referral_source": "arrival_mode", "medical_aid": "insurance", "end": "discharge_time_utc",
                "outcome": "status"}))
        for key, (entity, mapping) in child_maps.items():
            items = enc.get(key)
            if items is None:
                continue
            if isinstance(items, dict):  # 'discharge' is an object when there is exactly one
                items = [items]
            for j, item in enumerate(items):
                raw = dict(item, encounter_id=eid)
                r = _rec(S, entity, f"{loc}.{key}[{j}]", raw, dict(mapping, encounter_id="admission_id"))
                if entity == "triage" and isinstance(r["symptoms"], list):
                    r["symptoms"] = ", ".join(r["symptoms"])
                out[entity].append(r)
    return out, [], doc["facility"]["codebook"]


def read_all():
    """Return ({source: {entity: [records]}}, [structural rejects], D's embedded codebook)."""
    a, ra = read_source_a()
    b, rb = read_source_b()
    c, rc = read_source_c()
    d, rd, d_codebook = read_source_d()
    return {"A": a, "B": b, "C": c, "D": d}, ra + rb + rc + rd, d_codebook
