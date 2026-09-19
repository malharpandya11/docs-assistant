const TOKEN_KEY = 'chatbot.authToken'
const EMAIL_KEY = 'chatbot.authEmail'

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function getStoredEmail() {
  try {
    return localStorage.getItem(EMAIL_KEY)
  } catch {
    return null
  }
}

export function setSession(token, email) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(EMAIL_KEY, email)
  } catch {
    // localStorage unavailable (private mode) — session just won't persist
  }
}

export function clearSession() {
  try {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
  } catch {
    // ignore
  }
}

export function isLoggedIn() {
  return !!getToken()
}
