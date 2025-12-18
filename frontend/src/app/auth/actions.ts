'use server';

import { redirect } from 'next/navigation';
import { cookies, headers } from 'next/headers';

// 从环境变量读取API_BASE，如果没有则使用默认值
const getAPIBase = () => {
  // 对于 Server Actions，始终使用内部 Docker 网络 hostname
  // 这样可以确保容器之间的通信正常
  if (process.env.NEXT_PUBLIC_BACKEND_URL) {
    return process.env.NEXT_PUBLIC_BACKEND_URL;
  }
  
  // Docker 内部网络的 hostname（后端监听 8000 端口）
  return 'http://backend:8000/v1';
};

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
      return { message: data.detail || 'Invalid email or password' };
    }

    // 存储token到cookie
    const cookieStore = await cookies();
    cookieStore.set('auth_token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60, // 7 days
    });

    // 重定向到仪表板
    const finalReturnUrl = returnUrl || '/dashboard';
    redirect(finalReturnUrl);
  } catch (error: any) {
    // Log the actual error for debugging
    console.error('Login error:', error);
    
    // Don't show network errors or redirect errors
    if (error?.message?.includes('NEXT_REDIRECT')) {
      throw error;
    }
    
    return { message: error?.message || 'An error occurred. Please try again.' };
  }
}

export async function signUpWithPassword(prevState: any, formData: FormData) {
  const email = formData.get('email') as string;
  const password = formData.get('password') as string;
  const confirmPassword = formData.get('confirmPassword') as string;
  const returnUrl = formData.get('returnUrl') as string | undefined;

  if (!email || !email.includes('@')) {
    return { message: 'Please enter a valid email address' };
  }

  if (!password || password.length < 6) {
    return { message: 'Password must be at least 6 characters' };
  }

  if (password !== confirmPassword) {
    return { message: 'Passwords do not match' };
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
      return { message: data.detail || 'Could not create account' };
    }

    // 存储token到cookie
    const cookieStore = await cookies();
    cookieStore.set('auth_token', data.access_token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60, // 7 days
    });

    // 重定向到仪表板
    const finalReturnUrl = returnUrl || '/dashboard';
    redirect(finalReturnUrl);
  } catch (error: any) {
    // Log the actual error for debugging
    console.error('Registration error:', error);
    
    // Don't show network errors or redirect errors
    if (error?.message?.includes('NEXT_REDIRECT')) {
      throw error;
    }
    
    return { message: error?.message || 'An error occurred. Please try again.' };
  }
}

export async function signOut() {
  // Clear auth token cookie
  const cookieStore = await cookies();
  cookieStore.delete('auth_token');
  return redirect('/');
}
