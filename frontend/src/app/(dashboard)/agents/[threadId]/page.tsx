'use client';

// Disable static generation since this page uses client-side features
export const dynamic = 'force-dynamic';

import React from 'react';
import {
  ThreadParams,
} from '@/components/thread/types';
import { RedirectPage } from './redirect-page';

export default function ThreadPage({
  params,
}: {
  params: Promise<ThreadParams>;
}) {
  const unwrappedParams = React.use(params);
  return <RedirectPage threadId={unwrappedParams.threadId} />;
}