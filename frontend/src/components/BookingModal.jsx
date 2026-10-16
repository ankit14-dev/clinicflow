import { useState } from 'react';
import { api } from '../api.js';
import { defaultSlot } from '../format.js';
import Modal from './Modal.jsx';

export default function BookingModal({ doctors, patients, preset = {}, act, onClose }) {
  const active = doctors.filter((d) => d.is_active);
  const slot = defaultSlot();
  const [form, setForm] = useState({
    patient_id: preset.patient_id ?? patients[0]?.id ?? 'new',
    doctor_id: preset.doctor_id ?? active[0]?.id ?? '',
    date: slot.date,
    time: slot.time,
    duration_minutes: 30,
    reason: '',
    notes: '',
    new_name: '',
    new_phone: '',
  });
  const [saving, setSaving] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });
  const isNewPatient = form.patient_id === 'new';

  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    const ok = await act(async () => {
      let patientId = Number(form.patient_id);
      if (isNewPatient) {
        patientId = (await api.patients.create({ full_name: form.new_name, phone: form.new_phone })).id;
      }
      await api.appointments.create({
        patient_id: patientId,
        doctor_id: Number(form.doctor_id),
        // the browser's local time -> absolute UTC instant for the API
        scheduled_at: new Date(`${form.date}T${form.time}`).toISOString(),
        duration_minutes: Number(form.duration_minutes),
        reason: form.reason,
        notes: form.notes,
      });
    }, 'Appointment booked');
    setSaving(false);
    if (ok) onClose();
  };

  return (
    <Modal title="Book appointment" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Patient
          <select value={form.patient_id} onChange={set('patient_id')} required>
            {patients.map((p) => <option key={p.id} value={p.id}>{p.full_name} · {p.phone}</option>)}
            <option value="new">+ New patient…</option>
          </select>
        </label>

        {isNewPatient && (
          <div className="form-row">
            <label>
              Full name
              <input value={form.new_name} onChange={set('new_name')} required minLength={2} autoFocus />
            </label>
            <label>
              Phone
              <input value={form.new_phone} onChange={set('new_phone')} required minLength={6} inputMode="tel" />
            </label>
          </div>
        )}

        <label>
          Doctor
          <select value={form.doctor_id} onChange={set('doctor_id')} required>
            {active.length === 0 && <option value="">No doctor on duty</option>}
            {active.map((d) => <option key={d.id} value={d.id}>{d.full_name} — {d.specialty}</option>)}
          </select>
        </label>

        <div className="form-row">
          <label>
            Date
            <input type="date" value={form.date} min={slot.date} onChange={set('date')} required />
          </label>
          <label>
            Time
            <input type="time" value={form.time} step={900} onChange={set('time')} required />
          </label>
          <label>
            Duration
            <select value={form.duration_minutes} onChange={set('duration_minutes')}>
              {[15, 30, 45, 60].map((m) => <option key={m} value={m}>{m} min</option>)}
            </select>
          </label>
        </div>

        <label>
          Reason for visit
          <input value={form.reason} onChange={set('reason')} required minLength={3} maxLength={300} placeholder="e.g. Follow-up, fever, annual check-up" />
        </label>
        <label>
          <span>Notes <span className="muted">(optional)</span></span>
          <textarea value={form.notes} onChange={set('notes')} rows={2} />
        </label>

        <footer className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={saving || active.length === 0}>
            {saving ? 'Booking…' : 'Book appointment'}
          </button>
        </footer>
      </form>
    </Modal>
  );
}
