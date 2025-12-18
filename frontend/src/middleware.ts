import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { locales, defaultLocale, type Locale } from '@/i18n/config';
import { detectBestLocaleFromHeaders } from '@/lib/utils/geo-detection-server';

// Marketing pages that support locale routing for SEO (/de, /it, etc.)
const MARKETING_ROUTES = [
  '/',
  '/suna',
  '/enterprise',
  '/legal',
  '/support',
  '/templates',
];

// Routes that don't require authentication
const PUBLIC_ROUTES = [
  '/', // Homepage should be public!
  '/auth',
  '/auth/callback',
  '/auth/signup',
  '/auth/forgot-password',
  '/auth/reset-password',
  '/legal',
  '/api/auth',
  '/share', // Shared content should be public
  '/templates', // Template pages should be public
  '/enterprise', // Enterprise page should be public
  '/master-login', // Master password admin login
  '/support', // Support page should be public
  '/suna', // Kortix rebrand page should be public for SEO
  '/help', // Help center and documentation should be public
  '/credits-explained', // Credits explained page should be public
  '/agents-101', 
  // Add locale routes for marketing pages
  ...locales.flatMap(locale => MARKETING_ROUTES.map(route => `/${locale}${route === '/' ? '' : route}`)),
];

// Routes that require authentication but are related to setup
const BILLING_ROUTES = [
  '/activate-trial',
  '/setting-up',
];

// Routes that require authentication and active subscription
const PROTECTED_ROUTES = [
  '/dashboard',
  '/agents',
  '/projects',
  '/settings',
];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Skip middleware for static files and API routes
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/favicon') ||
    pathname.includes('.') ||
    pathname.startsWith('/api/')
  ) {
    return NextResponse.next();
  }

  // Handle Supabase verification redirects at root level
  // Supabase sometimes redirects to root (/) instead of /auth/callback
  // Detect authentication parameters and redirect to proper callback handler
  if (pathname === '/' || pathname === '') {
    const searchParams = request.nextUrl.searchParams;
    const code = searchParams.get('code');
    const token = searchParams.get('token');
    const type = searchParams.get('type');
    const error = searchParams.get('error');
    
    // If we have Supabase auth parameters, redirect to /auth/callback
    // Note: Mobile apps use direct deep links and bypass this route
    if (code || token || type || error) {
      const callbackUrl = new URL('/auth/callback', request.url);
      
      // Preserve all query parameters
      searchParams.forEach((value, key) => {
        callbackUrl.searchParams.set(key, value);
      });
      
      console.log('🔄 Redirecting Supabase verification from root to /auth/callback');
      return NextResponse.redirect(callbackUrl);
    }
  }

  // Extract path segments
  const pathSegments = pathname.split('/').filter(Boolean);
  const firstSegment = pathSegments[0];
  
  // Check if first segment is a locale (e.g., /de, /it, /de/suna)
  if (firstSegment && locales.includes(firstSegment as Locale)) {
    const locale = firstSegment as Locale;
    const remainingPath = '/' + pathSegments.slice(1).join('/') || '/';
    
    // Verify remaining path is a marketing route
    const isRemainingPathMarketing = MARKETING_ROUTES.some(route => {
      if (route === '/') {
        return remainingPath === '/' || remainingPath === '';
      }
      return remainingPath === route || remainingPath.startsWith(route + '/');
    });
    
    if (isRemainingPathMarketing) {
      // Rewrite /de to /, /de/suna to /suna, etc.
      const response = NextResponse.rewrite(new URL(remainingPath, request.url));
      response.cookies.set('locale', locale, {
        path: '/',
        maxAge: 31536000, // 1 year
        sameSite: 'lax',
      });
      
      // Store locale in headers so next-intl can pick it up
      response.headers.set('x-locale', locale);
      
      return response;
    }
  }
  
  // Check if this is a marketing route (without locale prefix)
  const isMarketingRoute = MARKETING_ROUTES.some(route => 
    pathname === route || pathname.startsWith(route + '/')
  );

  // Auto-redirect based on geo-detection for marketing pages
  // Only redirect if:
  // 1. User is visiting a marketing route without locale prefix
  // 2. User doesn't have an explicit preference (no cookie, no user metadata)
  // 3. Detected locale is not English (default)
  if (isMarketingRoute && (!firstSegment || !locales.includes(firstSegment as Locale))) {
    // Check if user has explicit preference in cookie
    const localeCookie = request.cookies.get('locale')?.value;
    const hasExplicitPreference = !!localeCookie && locales.includes(localeCookie as Locale);
    
    // For now, skip user metadata check (would require auth token)
    // Just use geo-detection
    if (!hasExplicitPreference) {
      const acceptLanguage = request.headers.get('accept-language');
      
      const detectedLocale = detectBestLocaleFromHeaders(acceptLanguage);
      
      // Only redirect if detected locale is not English (default)
      // This prevents unnecessary redirects for English speakers
      if (detectedLocale !== defaultLocale) {
        const redirectUrl = new URL(request.url);
        redirectUrl.pathname = `/${detectedLocale}${pathname === '/' ? '' : pathname}`;
        
        const redirectResponse = NextResponse.redirect(redirectUrl);
        // Set cookie so we don't redirect again on next visit
        redirectResponse.cookies.set('locale', detectedLocale, {
          path: '/',
          maxAge: 31536000, // 1 year
          sameSite: 'lax',
        });
        return redirectResponse;
      }
    }
  }

  // Allow all public routes without any checks
  if (PUBLIC_ROUTES.some(route => pathname === route || pathname.startsWith(route + '/'))) {
    return NextResponse.next();
  }

  // Everything else requires authentication
  let supabaseResponse = NextResponse.next({
    request,
  });

  // For now, skip authentication checks in middleware
  // Authentication is handled at the page/API level via auth tokens
  return supabaseResponse;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     * - root path (/)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}; 