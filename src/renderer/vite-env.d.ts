/// <reference types="vite/client" />

import type { StorageHelperApi } from '../preload/preload';

declare global {
  interface Window {
    storageHelper: StorageHelperApi;
  }
}
