// Note: Auth callback has been disabled as part of Supabase migration to private deployment
// This route is kept for compatibility but redirects to home page
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Auth Callback Route - Web Handler
 * 
 * Handles authentication callbacks for web browsers.
 * 
 * Flow:
 * - If app is installed: Universal Links intercept HTTPS URLs and open app directly (bypasses this)
 * - If app is NOT installed: Opens in browser → this route handles auth and redirects to dashboard
 */

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const requestOrigin = request.nextUrl.origin
  const baseUrl = requestOrigin || process.env.NEXT_PUBLIC_URL || 'http://localhost:3000'
  const error = searchParams.get('error')

  // Handle errors - redirect to auth page
  if (error) {
    console.error('❌ Auth callback error:', error)
    return NextResponse.redirect(`${baseUrl}/auth?error=${encodeURIComponent(error)}`)
  }

  // Note: OAuth callbacks are no longer supported in private deployment
  // Redirect to auth page
  console.log('🔄 Auth callback received - redirecting to auth page')
  return NextResponse.redirect(`${baseUrl}/auth`)
}
