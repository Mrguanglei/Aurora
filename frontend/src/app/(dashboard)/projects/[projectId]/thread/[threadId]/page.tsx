'use client';

// Disable static generation since this page uses client-side features
export const dynamic = 'force-dynamic';

import React from 'react';
import { ThreadComponent } from '@/components/thread/ThreadComponent';

export default function ThreadPage({
  params,
}: {
  params: Promise<{
    projectId: string;
    threadId: string;
  }>;
}) {
  const unwrappedParams = React.use(params);
  const { projectId, threadId } = unwrappedParams;

  return <ThreadComponent projectId={projectId} threadId={threadId} />;
}
