import type { WarehouseSchema } from "./warehouseTypes";
import { WAREHOUSE_FIXTURE_SCHEMAS } from "./warehouseFixtures";

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000/api";

// W29'da: GET ${BASE_URL}/warehouse/schemas ile swap et, fixture satırını kaldır.
export async function getWarehouseSchemas(): Promise<WarehouseSchema[]> {
  return Promise.resolve(WAREHOUSE_FIXTURE_SCHEMAS); // W29'da: live swap
}

// W29'da: POST ${BASE_URL}/warehouse/schemas/generate ile swap et.
export async function generateWarehouseSchema(
  definition: unknown,
): Promise<WarehouseSchema> {
  // M8'de generation API-only; bu fonksiyon sayfadan çağrılmaz.
  // W29'da aktif hale gelir.
  void definition;
  void BASE_URL;
  return Promise.reject(new Error("Generation is API-only in M8."));
}
