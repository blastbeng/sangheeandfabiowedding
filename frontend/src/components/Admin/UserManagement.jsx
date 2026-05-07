import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';

const UserManagement = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [formData, setFormData] = useState({
    username: '', email: '', first_name: '', last_name: '',
    is_staff: false, is_active: true, password: ''
  });
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchUsers = () => {
    fetch(`${API_URL}/api/auth/admin/users/`, {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
    })
      .then(res => res.json())
      .then(data => { setUsers(data); setLoading(false); })
      .catch(err => { 
        logger.error('[UserManagement] Users fetch error:', err); 
        setLoading(false); 
      });
  };

  useEffect(() => { fetchUsers(); }, [API_URL]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const url = editingUser 
      ? `${API_URL}/api/auth/admin/users/${editingUser.id}/`
      : `${API_URL}/api/auth/admin/users/`;
    const method = editingUser ? 'PUT' : 'POST';

    try {
      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify(formData)
      });
      if (res.ok) {
        fetchUsers();
        setShowModal(false);
        setEditingUser(null);
        setFormData({ username: '', email: '', first_name: '', last_name: '', is_staff: false, is_active: true, password: '' });
      }
    } catch (err) {
      logger.error('[UserManagement] User save error:', err);
      logger.error('[UserManagement] Form data:', formData);
    }
  };

  const handleDelete = async (userId) => {
    if (!confirm('Delete this user?')) return;
    try {
      const res = await fetch(`${API_URL}/api/auth/admin/users/${userId}/`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('accessToken')}` }
      });
      if (res.ok) fetchUsers();
    } catch (err) {
      logger.error('[UserManagement] Delete error for user:', userId, err);
    }
  };

  const handleToggleStaff = async (userId) => {
    try {
      const res = await fetch(`${API_URL}/api/auth/admin/users/${userId}/toggle-staff/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
        },
        body: JSON.stringify({ is_staff: true })
      });
      if (res.ok) fetchUsers();
    } catch (err) {
      logger.error('[UserManagement] Toggle staff error for user:', userId, err);
    }
  };

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600">Loading users...</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="wedding-card p-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-3xl wedding-title">👥 User Management</h2>
          <button onClick={() => setShowModal(true)} className="wedding-btn">➕ Add User</button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-pink-200">
                <th className="text-left py-3 text-pink-600">Username</th>
                <th className="text-left py-3 text-pink-600">Email</th>
                <th className="text-left py-3 text-pink-600">Name</th>
                <th className="text-left py-3 text-pink-600">Role</th>
                <th className="text-left py-3 text-pink-600">Status</th>
                <th className="text-left py-3 text-pink-600">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b border-pink-100 hover:bg-pink-50">
                  <td className="py-3">{user.username}</td>
                  <td className="py-3">{user.email}</td>
                  <td className="py-3">{user.first_name} {user.last_name}</td>
                  <td className="py-3">
                    {user.is_superuser ? '👑 Superadmin' : user.is_staff ? '⭐ Admin' : '👤 User'}
                  </td>
                  <td className="py-3">
                    <span className={`status-badge ${user.is_active ? 'status-approved' : 'status-rejected'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-3">
                    <button onClick={() => { setEditingUser(user); setFormData({...user, password: ''}); setShowModal(true); }} className="text-blue-500 hover:text-blue-700 text-sm mr-2">✏️ Edit</button>
                    {!user.is_superuser && (
                      <button onClick={() => handleDelete(user.id)} className="text-red-500 hover:text-red-700 text-sm">🗑️ Delete</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="wedding-card p-6 max-w-md w-full">
            <h3 className="text-xl font-bold mb-4 text-pink-600">{editingUser ? 'Edit User' : 'Add New User'}</h3>
            <form onSubmit={handleSubmit}>
              <input type="text" placeholder="Username" value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} className="wedding-input w-full mb-3" required />
              <input type="email" placeholder="Email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} className="wedding-input w-full mb-3" required />
              <input type="text" placeholder="First Name" value={formData.first_name} onChange={(e) => setFormData({...formData, first_name: e.target.value})} className="wedding-input w-full mb-3" />
              <input type="text" placeholder="Last Name" value={formData.last_name} onChange={(e) => setFormData({...formData, last_name: e.target.value})} className="wedding-input w-full mb-3" />
              {!editingUser && (
                <input type="password" placeholder="Password" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} className="wedding-input w-full mb-3" required={!editingUser} />
              )}
              <label className="flex items-center mb-3">
                <input type="checkbox" checked={formData.is_staff} onChange={(e) => setFormData({...formData, is_staff: e.target.checked})} className="mr-2" />
                Admin Access
              </label>
              <label className="flex items-center mb-4">
                <input type="checkbox" checked={formData.is_active} onChange={(e) => setFormData({...formData, is_active: e.target.checked})} className="mr-2" />
                Active
              </label>
              <div className="flex gap-2">
                <button type="submit" className="flex-1 wedding-btn">Save</button>
                <button type="button" onClick={() => { setShowModal(false); setEditingUser(null); }} className="flex-1 bg-gray-400 text-white px-4 py-2 rounded hover:bg-gray-500">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
