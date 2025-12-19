import { PhoneVerificationPage } from "@/components/auth/phone-verification/phone-verification-page";

// Disable static generation since this page uses client-side auth
export const dynamic = 'force-dynamic';

export default function PhoneVerificationRoute() {
  return <PhoneVerificationPage />;
}