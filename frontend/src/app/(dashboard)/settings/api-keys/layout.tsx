// Disable static generation to avoid Supabase client errors during build
export const dynamic = 'force-dynamic';
export const revalidate = 0;

export default async function APIKeysLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <>{children}</>;
}
