import createClient from "openapi-fetch";

import type { paths } from "./cloudopt-api";

/** Browser: empty base uses same-origin `/api/...` with Next rewrites. Override with NEXT_PUBLIC_CLOUDOPT_API_URL. */
export function getApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return process.env.NEXT_PUBLIC_CLOUDOPT_API_URL?.trim() || "";
}

export function createCloudoptClient() {
  return createClient<paths>({ baseUrl: getApiBaseUrl() });
}
