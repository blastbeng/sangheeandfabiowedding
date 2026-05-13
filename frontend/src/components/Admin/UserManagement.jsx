import { useEffect, useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import logger from '../../utils/logger';
import authFetch from '../../utils/authFetch';

const UserManagement = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [profilePicFile, setProfilePicFile] = useState(null);
  const [deletePicture, setDeletePicture] = useState(false);
  const [message, setMessage] = useState(null); // { type: 'success'|'error', text: '' }
  const [selectedUserIds, setSelectedUserIds] = useState([]);
  const [selectAll, setSelectAll] = useState(false);
  const fileInputRef = useRef(null);
  const [formData, setFormData] = useState({
    username: '', email: '', first_name: '', last_name: '',
    is_staff: false, is_active: true, email_verified: false, password: '', password_confirm: ''
  });
  const [filters, setFilters] = useState({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    role: '',
    status: ''
  });
  const API_URL = import.meta.env.VITE_API_URL;

  const fetchUsers = () => {
    authFetch(`${API_URL}/api/auth/admin/users/`)
      .then(res => res.json())
      .then(data => { setUsers(data); setLoading(false); })
      .catch(err => { 
        logger.error('[UserManagement] Users fetch error:', err); 
        setLoading(false); 
      });
  };

  useEffect(() => { fetchUsers(); }, [API_URL]);

  const resetModalState = () => {
    setProfilePicFile(null);
    setDeletePicture(false);
    setMessage(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null); // clear previous messages
    const url = editingUser 
      ? `${API_URL}/api/auth/admin/users/${editingUser.id}/`
      : `${API_URL}/api/auth/admin/users/`;
    const method = editingUser ? 'PUT' : 'POST';

    try {
      let res;
      if (profilePicFile) {
        // Use FormData for file upload
        const fd = new FormData();
        fd.append('username', formData.username);
        fd.append('email', formData.email);
        fd.append('first_name', formData.first_name);
        fd.append('last_name', formData.last_name);
        fd.append('is_staff', formData.is_staff);
        fd.append('is_active', formData.is_active);
        fd.append('email_verified', formData.email_verified);
        if (formData.password) fd.append('password', formData.password);
        if (formData.password_confirm) fd.append('password_confirm', formData.password_confirm);
        fd.append('profile_picture', profilePicFile);
        res = await authFetch(url, {
          method,
          body: fd,
        });
      } else if (deletePicture) {
        // Send JSON with remove_profile_picture flag
        const body = { ...formData };
        body.remove_profile_picture = true;
        res = await authFetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        });
      } else {
        // Regular JSON update
        res = await authFetch(url, {
          method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        });
      }
      if (res.ok) {
        setMessage({ type: 'success', text: t('admin_user_saved') });
        fetchUsers();
        // Close modal after a short delay so the admin sees the success message
        setTimeout(() => {
          setShowModal(false);
          setEditingUser(null);
          resetModalState();
          setFormData({ username: '', email: '', first_name: '', last_name: '', is_staff: false, is_active: true, email_verified: false, password: '', password_confirm: '' });
          setMessage(null);
        }, 1500);
      } else {
        const errorData = await res.json().catch(() => ({}));
        const errorText = errorData.detail || errorData.error || JSON.stringify(errorData);
        setMessage({ type: 'error', text: errorText });
        logger.error('[UserManagement] User save failed:', res.status, errorData);
      }
    } catch (err) {
      setMessage({ type: 'error', text: t('admin_network_error') });
      logger.error('[UserManagement] User save error:', err);
    }
  };

  const handleDelete = async (userId) => {
    if (!confirm(t('admin_delete_user_confirm'))) return;
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/users/${userId}/`, {
        method: 'DELETE'
      });
      if (res.ok) fetchUsers();
    } catch (err) {
      logger.error('[UserManagement] Delete error for user:', userId, err);
    }
  };

  const handleToggleStaff = async (userId) => {
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/users/${userId}/toggle-staff/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_staff: true })
      });
      if (res.ok) fetchUsers();
    } catch (err) {
      logger.error('[UserManagement] Toggle staff error for user:', userId, err);
    }
  };

  const handleToggleActive = async (userId) => {
    const user = users.find(u => u.id === userId);
    if (!user) return;

    const isActive = user.email_verified && user.is_active;
    const payload = isActive
      ? { is_active: false }
      : { is_active: true, email_verified: true };

    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/users/${userId}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        fetchUsers();
      } else {
        const err = await res.json().catch(() => ({}));
        logger.error('[UserManagement] Toggle active failed:', err);
      }
    } catch (err) {
      logger.error('[UserManagement] Toggle active error:', err);
    }
  };

  const toggleSelectAll = () => {
    if (selectAll) {
      setSelectedUserIds([]);
    } else {
      setSelectedUserIds(filteredUsers.filter(u => !u.is_default_admin).map(u => u.id));
    }
    setSelectAll(!selectAll);
  };

  const toggleSelectItem = (id) => {
    const user = users.find(u => u.id === id);
    if (user?.is_default_admin) return;
    setSelectedUserIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  const handleBulkAction = async (action) => {
    try {
      const res = await authFetch(`${API_URL}/api/auth/admin/users/bulk/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_ids: selectedUserIds, action })
      });
      if (res.ok) {
        fetchUsers();
        setSelectedUserIds([]);
        setSelectAll(false);
      } else {
        const err = await res.json().catch(() => ({}));
        logger.error('[UserManagement] Bulk action failed:', err);
      }
    } catch (err) {
      logger.error('[UserManagement] Bulk action error:', err);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setProfilePicFile(e.target.files[0]);
      setDeletePicture(false);
    } else {
      setProfilePicFile(null);
    }
  };

  const handleDeletePicture = () => {
    setDeletePicture(true);
    setProfilePicFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleCancelDeletePicture = () => {
    setDeletePicture(false);
  };

  const handleClearFile = () => {
    setProfilePicFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const filteredUsers = users.filter(user => {
    const matchUsername = user.username.toLowerCase().includes(filters.username.toLowerCase());
    const matchEmail = user.email.toLowerCase().includes(filters.email.toLowerCase());
    const matchFirstName = user.first_name.toLowerCase().includes(filters.first_name.toLowerCase());
    const matchLastName = user.last_name.toLowerCase().includes(filters.last_name.toLowerCase());
    const matchRole = filters.role === '' || 
      (filters.role === 'superadmin' && user.is_superuser) ||
      (filters.role === 'admin' && user.is_staff && !user.is_superuser) ||
      (filters.role === 'user' && !user.is_staff);
    const matchStatus = filters.status === '' || 
      (filters.status === 'unverified' && !user.email_verified) ||
      (filters.status === 'inactive' && user.email_verified && !user.is_active) ||
      (filters.status === 'active' && user.email_verified && user.is_active);
    return matchUsername && matchEmail && matchFirstName && matchLastName && matchRole && matchStatus;
  });

  if (loading) {
    return (
      <div className="text-center py-20">
        <span className="text-5xl heart-decoration inline-block">💝</span>
        <p className="mt-4 text-gray-600">{t('admin_users_loading')}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-4">
      <div className="wedding-card p-8">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-3xl wedding-title">{t('admin_users_title')}</h2>
          <button onClick={() => { setEditingUser(null); setFormData({ username: '', email: '', first_name: '', last_name: '', is_staff: false, is_active: true, email_verified: false, password: '', password_confirm: '' }); resetModalState(); setShowModal(true); }} className="wedding-btn">{t('admin_add_user')}</button>
        </div>

        {selectedUserIds.length > 0 && (
          <div className="flex items-center gap-2 mb-4 p-3 bg-pink-50 rounded">
            <span className="text-sm text-pink-700">{t('admin_selected_count', { count: selectedUserIds.length })}</span>
            <button onClick={() => handleBulkAction('activate')} className="wedding-btn text-xs py-1 px-3">{t('admin_activate_selected')}</button>
            <button onClick={() => handleBulkAction('deactivate')} className="wedding-btn text-xs py-1 px-3 bg-gray-400 hover:bg-gray-500">{t('admin_deactivate_selected')}</button>
            <button onClick={() => handleBulkAction('verify_email')} className="wedding-btn text-xs py-1 px-3">{t('admin_verify_email_selected')}</button>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-pink-200">
                <th className="py-3">
                  <input
                    type="checkbox"
                    checked={selectAll}
                    onChange={toggleSelectAll}
                    className="mr-2"
                  />
                </th>
                <th className="text-left py-3 text-pink-600">{t('admin_users_col_picture')}</th>
                <th className="text-left py-3 text-pink-600">{t('admin_users_col_username')}</th>
                <th className="text-left py-3 text-pink-600">{t('admin_users_col_role')}</th>
                <th className="text-left py-3 text-pink-600">{t('admin_users_col_status')}</th>
                <th className="text-left py-3 text-pink-600">{t('admin_users_col_actions')}</th>
              </tr>
              <tr className="border-b border-pink-100">
                <th></th>
                <th></th>
                <th className="py-2">
                  <input
                    type="text"
                    placeholder={t('filter_username')}
                    value={filters.username}
                    onChange={(e) => setFilters({...filters, username: e.target.value})}
                    className="wedding-input w-full text-xs py-1"
                  />
                </th>
                <th className="py-2">
                  <select
                    value={filters.role}
                    onChange={(e) => setFilters({...filters, role: e.target.value})}
                    className="wedding-input w-full text-xs py-1"
                  >
                    <option value="">{t('all')}</option>
                    <option value="superadmin">{t('admin_role_superadmin')}</option>
                    <option value="admin">{t('admin_role_admin')}</option>
                    <option value="user">{t('admin_role_user')}</option>
                  </select>
                </th>
                <th className="py-2">
                  <select
                    value={filters.status}
                    onChange={(e) => setFilters({...filters, status: e.target.value})}
                    className="wedding-input w-full text-xs py-1"
                  >
                    <option value="">{t('all')}</option>
                    <option value="unverified">{t('admin_status_unverified')}</option>
                    <option value="inactive">{t('admin_status_inactive')}</option>
                    <option value="active">{t('admin_status_active')}</option>
                  </select>
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filteredUsers.map((user) => (
                <tr key={user.id} className="border-b border-pink-100 hover:bg-pink-50">
                  <td className="py-3">
                    <input
                      type="checkbox"
                      checked={selectedUserIds.includes(user.id)}
                      onChange={() => toggleSelectItem(user.id)}
                      disabled={user.is_default_admin}
                      className="mr-2"
                    />
                  </td>
                  <td className="py-3">
                    <img
                      src={user.profile_picture_url || 'https://i.imgur.com/V4RclNb.png'}
                      alt=""
                      className="w-10 h-10 object-cover rounded-full border border-pink-200"
                      onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                    />
                  </td>
                  <td className="py-3">{user.username}</td>
                  <td className="py-3">
                    {user.is_superuser ? t('admin_role_superadmin') : user.is_staff ? t('admin_role_admin') : t('admin_role_user')}
                  </td>
                  <td className="py-3 whitespace-nowrap">
                    {(() => {
                      if (!user.email_verified) {
                        return <span className="status-badge status-pending">{t('admin_status_unverified')}</span>;
                      } else if (!user.is_active) {
                        return <span className="status-badge status-rejected">{t('admin_status_inactive')}</span>;
                      } else {
                        return <span className="status-badge status-approved">{t('admin_status_active')}</span>;
                      }
                    })()}
                  </td>
                  <td className="py-3">
                    <button onClick={() => { setEditingUser(user); setFormData({...user, password: '', password_confirm: ''}); resetModalState(); setShowModal(true); }} className="text-blue-500 hover:text-blue-700 text-sm mr-2">{t('admin_edit')}</button>
                    {!user.is_default_admin && (
                      <button
                        onClick={() => handleToggleActive(user.id)}
                        className="text-green-600 hover:text-green-800 text-sm mr-2"
                      >
                        {user.email_verified && user.is_active ? t('admin_deactivate') : t('admin_activate')}
                      </button>
                    )}
                    {!user.is_default_admin && (
                      <button onClick={() => handleDelete(user.id)} className="text-red-500 hover:text-red-700 text-sm">{t('admin_delete')}</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 overflow-y-auto z-50">
          <div className="flex items-center justify-center min-h-screen p-4">
            <div className="wedding-card p-6 max-w-md w-full">
              <h3 className="text-xl font-bold mb-4 text-pink-600">{editingUser ? t('admin_edit_user') : t('admin_add_new_user')}</h3>
              {message && (
                <div className={`mb-4 p-3 rounded text-sm ${
                  message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                }`}>
                  {message.text}
                </div>
              )}
              <form onSubmit={handleSubmit}>
                <input type="text" placeholder={t('admin_form_username')} value={formData.username} onChange={(e) => setFormData({...formData, username: e.target.value})} className="wedding-input w-full mb-3" required />
                <input type="email" placeholder={t('admin_form_email')} value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} className="wedding-input w-full mb-3" required />
                <input type="text" placeholder={t('admin_form_first_name')} value={formData.first_name} onChange={(e) => setFormData({...formData, first_name: e.target.value})} className="wedding-input w-full mb-3" />
                <input type="text" placeholder={t('admin_form_last_name')} value={formData.last_name} onChange={(e) => setFormData({...formData, last_name: e.target.value})} className="wedding-input w-full mb-3" />
                {/* Password fields – always shown for new users, optional for editing */}
                <input
                  type="password"
                  placeholder={t('admin_form_password')}
                  value={formData.password}
                  onChange={(e) => setFormData({...formData, password: e.target.value})}
                  className="wedding-input w-full mb-3"
                  required={!editingUser}
                />
                <input
                  type="password"
                  placeholder={t('admin_form_password_confirm')}
                  value={formData.password_confirm || ''}
                  onChange={(e) => setFormData({...formData, password_confirm: e.target.value})}
                  className="wedding-input w-full mb-3"
                  required={!editingUser}
                />
                <label className="flex items-center mb-3">
                  <input
                    type="checkbox"
                    checked={formData.is_staff}
                    onChange={(e) => setFormData({...formData, is_staff: e.target.checked})}
                    disabled={editingUser?.is_default_admin}
                    className="mr-2"
                  />
                  {t('admin_form_admin_access')}
                </label>
                <label className="flex items-center mb-3">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({...formData, is_active: e.target.checked})}
                    disabled={editingUser?.is_default_admin}
                    className="mr-2"
                  />
                  {t('admin_form_active')}
                </label>
                <label className="flex items-center mb-4">
                  <input
                    type="checkbox"
                    checked={formData.email_verified}
                    onChange={(e) => setFormData({...formData, email_verified: e.target.checked})}
                    disabled={editingUser?.is_default_admin}
                    className="mr-2"
                  />
                  {t('admin_form_email_verified')}
                </label>

                {/* Profile Picture Section */}
                <div className="mt-2 pt-4 border-t border-pink-200 mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('admin_form_profile_picture')}
                  </label>
                  {editingUser && (
                    <div className="mb-3 flex items-center gap-3">
                      <img
                        src={editingUser.profile_picture_url || 'https://i.imgur.com/V4RclNb.png'}
                        alt=""
                        className={`w-16 h-16 object-cover rounded-full border border-pink-200${deletePicture ? ' opacity-40' : ''}`}
                        onError={(e) => { e.target.src = 'https://i.imgur.com/V4RclNb.png'; }}
                      />
                      {!deletePicture ? (
                        <button
                          type="button"
                          onClick={handleDeletePicture}
                          className="text-red-500 hover:text-red-700 text-sm underline"
                        >
                          {t('admin_delete_picture')}
                        </button>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="text-red-500 text-sm font-medium">
                            {t('admin_picture_will_be_deleted')}
                          </span>
                          <button
                            type="button"
                            onClick={handleCancelDeletePicture}
                            className="text-gray-500 hover:text-gray-700 text-sm underline"
                          >
                            {t('admin_cancel_delete_picture')}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                  <div className="relative">
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="image/*"
                      onChange={handleFileChange}
                      className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-pink-50 file:text-pink-700 hover:file:bg-pink-100"
                    />
                    {profilePicFile && (
                      <div className="mt-1 flex items-center gap-2">
                        <span className="text-sm text-gray-500">{profilePicFile.name}</span>
                        <button
                          type="button"
                          onClick={handleClearFile}
                          className="text-red-400 hover:text-red-600 text-sm"
                        >
                          ✕
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex gap-2">
                  <button type="submit" className="flex-1 wedding-btn">{t('admin_save')}</button>
                  <button type="button" onClick={() => { setShowModal(false); setEditingUser(null); resetModalState(); }} className="flex-1 bg-gray-400 text-white px-4 py-2 rounded hover:bg-gray-500">{t('admin_cancel')}</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UserManagement;
