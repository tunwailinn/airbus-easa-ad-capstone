import createClient from "openapi-fetch";
import type { paths } from "@/generated/api";

export const API_BASE = process.env.NEXT_PUBLIC_ASSISTANT_API_URL ?? "http://127.0.0.1:8000";
export const api = createClient<paths>({ baseUrl: API_BASE });
