import { useState } from 'react';
import { api } from '../api.js';
import Modal from './Modal.jsx';

const SPECIALTIES = ['General Medicine', 'Cardiology', 'Pediatrics', 'Dermatology', 'Orthopedics', 'ENT', 'Gynecology', 'Neurology'];

export default function DoctorModal({ act, onClose }) {
  const [form, setForm] = useState({ full_name: 'Dr. ', specialty: SPECIALTIES[0], room: '', email: '' });
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    if (await act(() => api.doctors.create(form), `${form.full_name} added`)) onClose();
  };

  return (
    <Modal title="Add doctor" onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <label>
          Full name
          <input value={form.full_name} onChange={set('full_name')} required minLength={5} autoFocus />
        </label>
        <div className="form-row">
          <label>
            Specialty
            <select value={form.specialty} onChange={set('specialty')}>
              {SPECIALTIES.map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
          <label>
            Room
            <input value={form.room} onChange={set('room')} maxLength={20} />
          </label>
        </div>
        <label>
          <span>Email <span className="muted">(optional)</span></span>
          <input type="email" value={form.email} onChange={set('email')} />
        </label>
        <footer className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn btn-primary">Add doctor</button>
        </footer>
      </form>
    </Modal>
  );
}
