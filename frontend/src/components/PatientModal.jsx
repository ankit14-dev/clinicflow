import { useState } from 'react';
import { api } from '../api.js';
import Modal from './Modal.jsx';

export default function PatientModal({ act, onClose }) {
  const [form, setForm] = useState({ full_name: '', phone: '', email: '', date_of_birth: '' });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const payload = { ...form, date_of_birth: form.date_of_birth || null };
    if (await act(() => api.patients.create(payload), `${form.full_name} registered`)) onClose();
  };

  return (
    <Modal title="Register patient" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Full name
          <input value={form.full_name} onChange={set('full_name')} required minLength={2} autoFocus />
        </label>
        <div className="form-row">
          <label>
            Phone
            <input value={form.phone} onChange={set('phone')} required minLength={6} inputMode="tel" />
          </label>
          <label>
            Date of birth
            <input type="date" value={form.date_of_birth} onChange={set('date_of_birth')} />
          </label>
        </div>
        <label>
          <span>Email <span className="muted">(optional)</span></span>
          <input type="email" value={form.email} onChange={set('email')} />
        </label>
        <footer className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary">Register</button>
        </footer>
      </form>
    </Modal>
  );
}
