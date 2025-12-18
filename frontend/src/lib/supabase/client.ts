// Supabase removed - return mock client
export function createClient() {
  return {
    auth: {
      getSession: () => Promise.resolve({ data: { session: null }, error: null }),
      getUser: () => Promise.resolve({ data: { user: null }, error: null }),
      onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
      signOut: () => Promise.resolve({ error: null }),
      signUp: () => Promise.resolve({ error: null }),
      signInWithPassword: () => Promise.resolve({ error: null }),
    },
  } as any;
}
