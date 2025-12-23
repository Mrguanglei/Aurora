/**
 * File metadata cache store
 * 
 * Caches file metadata (size, type, etc.) for uploaded files
 * so we can display accurate file sizes even after the file
 * is sent in a message.
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface FileMetadata {
  path: string;
  size: number;
  type: string;
  name: string;
  uploadedAt: number; // timestamp
}

interface FileMetadataStore {
  fileMetadataMap: Record<string, FileMetadata>; // key: file path
  addFileMetadata: (metadata: FileMetadata) => void;
  addBulkFileMetadata: (metadataList: FileMetadata[]) => void;
  getFileMetadata: (path: string) => FileMetadata | undefined;
  removeFileMetadata: (path: string) => void;
  clearOldMetadata: (maxAgeMs: number) => void;
}

export const useFileMetadataStore = create<FileMetadataStore>()(
  persist(
    (set, get) => ({
      fileMetadataMap: {},

      addFileMetadata: (metadata) => {
        set((state) => ({
          fileMetadataMap: {
            ...state.fileMetadataMap,
            [metadata.path]: metadata,
          },
        }));
      },

      addBulkFileMetadata: (metadataList) => {
        set((state) => {
          const newMap = { ...state.fileMetadataMap };
          metadataList.forEach((metadata) => {
            newMap[metadata.path] = metadata;
          });
          return { fileMetadataMap: newMap };
        });
      },

      getFileMetadata: (path) => {
        return get().fileMetadataMap[path];
      },

      removeFileMetadata: (path) => {
        set((state) => {
          const newMap = { ...state.fileMetadataMap };
          delete newMap[path];
          return { fileMetadataMap: newMap };
        });
      },

      clearOldMetadata: (maxAgeMs = 7 * 24 * 60 * 60 * 1000) => {
        const now = Date.now();
        set((state) => {
          const newMap: Record<string, FileMetadata> = {};
          Object.entries(state.fileMetadataMap).forEach(([path, metadata]) => {
            if (now - metadata.uploadedAt < maxAgeMs) {
              newMap[path] = metadata;
            }
          });
          return { fileMetadataMap: newMap };
        });
      },
    }),
    {
      name: 'file-metadata-storage',
      // Only persist for 7 days
      version: 1,
    }
  )
);
