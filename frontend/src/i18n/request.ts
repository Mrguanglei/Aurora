import { getRequestConfig } from 'next-intl/server';
import { cookies, headers } from 'next/headers';
import { locales, defaultLocale, type Locale } from './config';

export default getRequestConfig(async ({ requestLocale }) => {
  let locale: Locale = defaultLocale;
  const cookieStore = await cookies();
  const headersList = await headers();
  
  // Priority 1: Check cookie (explicit user preference)
  // In private deployment, we rely on cookie for user language preference
  const localeCookie = cookieStore.get('locale')?.value;
  if (localeCookie && locales.includes(localeCookie as Locale)) {
    locale = localeCookie as Locale;
    return {
      locale,
      messages: (await import(`../../translations/${locale}.json`)).default
    };
  }
  
  // Priority 2: If locale is provided in the URL path (e.g., /de, /it), use it for marketing pages
  // This allows SEO-friendly URLs like /de, /it for marketing content
  // Only used if user hasn't set an explicit preference
  const urlLocale = requestLocale || headersList.get('x-locale');
  if (urlLocale && locales.includes(urlLocale as Locale)) {
    locale = urlLocale as Locale;
    return {
      locale,
      messages: (await import(`../../translations/${locale}.json`)).default
    };
  }
  
  // Priority 3: Try to detect from Accept-Language header (browser language)
  const acceptLanguage = headersList.get('accept-language');
  if (acceptLanguage) {
    const browserLocale = acceptLanguage.split(',')[0].split('-')[0].toLowerCase();
    if (locales.includes(browserLocale as Locale)) {
      locale = browserLocale as Locale;
    }
  }

  // Priority 4: Default to English
  return {
    locale,
    messages: (await import(`../../translations/${locale}.json`)).default
  };
});

