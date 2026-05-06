import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  it: {
    translation: {
      "Login": "Accedi",
      "Register": "Registrati",
      "Email": "Email",
      "Password": "Password",
      "Username": "Nome utente",
      "First Name": "Nome",
      "Last Name": "Cognome",
      "Profile": "Profilo",
      "Upload": "Carica",
      "My Uploads": "I miei caricamenti",
      "Gallery": "Galleria",
      "Moderation": "Moderazione",
      "Logout": "Esci",
      "Don't have an account?": "Non hai un account?",
      "Or login with": "O accedi con",
      "Update Profile": "Aggiorna profilo",
      "Change Password": "Cambia password",
      "Current Password": "Password corrente",
      "New Password": "Nuova password",
      "Confirm New Password": "Conferma nuova password",
      "Profile updated successfully": "Profilo aggiornato",
      "Password updated successfully": "Password aggiornata",
      "pending": "In attesa",
      "approved": "Approvato",
      "rejected": "Rifiutato",
      "Loading...": "Caricamento...",
      "Language": "Lingua",
      "Italiano": "Italiano",
      "English": "English",
      "한국어": "한국어"
    }
  },
  ko: {
    translation: {
      "Login": "로그인",
      "Register": "등록",
      "Email": "이메일",
      "Password": "비밀번호",
      "Username": "사용자명",
      "First Name": "이름",
      "Last Name": "성",
      "Profile": "프로필",
      "Upload": "업로드",
      "My Uploads": "내 업로드",
      "Gallery": "갤러리",
      "Moderation": "중재",
      "Logout": "로그아웃",
      "Don't have an account?": "계정이 없으신가요?",
      "Or login with": "또는 로그인",
      "Update Profile": "프로필 업데이트",
      "Change Password": "비밀번호 변경",
      "Current Password": "현재 비밀번호",
      "New Password": "새 비밀번호",
      "Confirm New Password": "새 비밀번호 확인",
      "Profile updated successfully": "프로필 업데이트 완료",
      "Password updated successfully": "비밀번호 업데이트 완료",
      "pending": "대기 중",
      "approved": "승인됨",
      "rejected": "거부됨",
      "Loading...": "로딩 중...",
      "Language": "언어",
      "Italiano": "Italiano",
      "English": "English",
      "한국어": "한국어"
    }
  },
  en: {
    translation: {
      "Login": "Login",
      "Register": "Register",
      "Email": "Email",
      "Password": "Password",
      "Username": "Username",
      "First Name": "First Name",
      "Last Name": "Last Name",
      "Profile": "Profile",
      "Upload": "Upload",
      "My Uploads": "My Uploads",
      "Gallery": "Gallery",
      "Moderation": "Moderation",
      "Logout": "Logout",
      "Don't have an account?": "Don't have an account?",
      "Or login with": "Or login with",
      "Update Profile": "Update Profile",
      "Change Password": "Change Password",
      "Current Password": "Current Password",
      "New Password": "New Password",
      "Confirm New Password": "Confirm New Password",
      "Profile updated successfully": "Profile updated successfully",
      "Password updated successfully": "Password updated successfully",
      "pending": "Pending",
      "approved": "Approved",
      "rejected": "Rejected",
      "Loading...": "Loading...",
      "Language": "Language",
      "Italiano": "Italiano",
      "English": "English",
      "한국어": "한국어"
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: localStorage.getItem('language') || 'it',
    fallbackLng: 'it',
    supportedLngs: ['it', 'ko', 'en'],
    interpolation: { escapeValue: false }
  });

export default i18n;
