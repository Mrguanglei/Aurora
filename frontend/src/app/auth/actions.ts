'use server';

import { redirect } from 'next/navigation';
import { cookies, headers } from 'next/headers';

// Server Actions 内部始终走 Docker 内部网络，避免受浏览器用的 URL 影响
const getAPIBase = () => {
  // 固定使用 Docker 网络里的 backend 服务名
  return 'http://backend:8011/v1';
};

// 注意：浏览器端请求使用 NEXT_PUBLIC_BACKEND_URL（通常是 http://localhost:8011/v1）,
// 见 docker-compose.yaml 中 frontend 的环境变量配置。

// ... existing code ...


export async function signIn(prevState: any, formData: FormData) {
  // Magic link authentication removed - using password authentication only
  return { message: 'Please use password authentication' };
}

export async function signUp(prevState: any, formData: FormData) {
  // Magic link authentication removed - using password authentication only
  return { message: 'Please use password authentication' };
}

export async function forgotPassword(prevState: any, formData: FormData) {
  // Password reset not yet implemented for local auth
  return { message: 'Password reset not available' };
}

export async function resetPassword(prevState: any, formData: FormData) {
  // Password reset not yet implemented for local auth
  return { message: 'Password reset not available' };
}

export async function resendMagicLink(prevState: any, formData: FormData) {
  // Magic link authentication removed - using password authentication only
  return { message: 'Please use password authentication' };
}

export async function signInWithPassword(prevState: any, formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const returnUrl = formData.get('returnUrl') as string | undefined;

  if (!email || !email.includes('@')) {
    return { message: 'Please enter a valid email address' };
  }

  if (!password || password.length < 6) {
    return { message: 'Password must be at least 6 characters' };
  }

  try {
    const API_BASE = getAPIBase();
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        password,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { message: data.detail || 'Invalid email or password', success: false };
    }

    // 不再在这里设置 HttpOnly cookie（前端需要能访问 token）
    // 直接把 token 返回给前端，由前端存到 localStorage
    return {
      success: true,
      redirectUrl: returnUrl || '/dashboard',
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    };
  } catch (error: any) {
    console.error('Login error:', error);
    return { message: error?.message || 'An error occurred. Please try again.', success: false };
  }
}

export async function signUpWithPassword(prevState: any, formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const confirmPassword = formData.get('confirmPassword') as string;
  const returnUrl = formData.get('returnUrl') as string | undefined;

  if (!email || !email.includes('@')) {
    return { message: 'Please enter a valid email address', success: false };
  }

  if (!password || password.length < 6) {
    return { message: 'Password must be at least 6 characters', success: false };
  }

  if (password !== confirmPassword) {
    return { message: 'Passwords do not match', success: false };
  }

  try {
    const API_BASE = getAPIBase();
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.trim().toLowerCase(),
        password,
        name: email.split('@')[0],
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      return { message: data.detail || 'Could not create account', success: false };
    }

    // 不再在这里设置 HttpOnly cookie（前端需要能访问 token）
    // 直接把 token 返回给前端，由前端存到 localStorage
    return {
      success: true,
      redirectUrl: returnUrl || '/dashboard',
      accessToken: data.access_token,
      refreshToken: data.refresh_token,
    };
  } catch (error: any) {
    console.error('Registration error:', error);
    return { message: error?.message || 'An error occurred. Please try again.', success: false };
  }
}

export async function signOut() {
  // Clear auth token cookie
  const cookieStore = await cookies();
  cookieStore.delete('auth_token');
  return redirect('/');
}
