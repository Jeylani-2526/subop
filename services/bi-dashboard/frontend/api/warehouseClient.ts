import type { WarehouseSchema } from "./warehouseTypes";

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
  "http://localhost:8000/api";

export async function getWarehouseSchemas(): Promise<WarehouseSchema[]> {
  const res = await fetch(`${BASE_URL}/warehouse/schemas`);
  if (!res.ok) throw new Error(`WAREHOUSE_API_ERROR: ${res.status}`);
  return res.json() as Promise<WarehouseSchema[]>;
}

export async function generateWarehouseSchema(
  definition: unknown,
): Promise<WarehouseSchema> {
  const res = await fetch(`${BASE_URL}/warehouse/schemas/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(definition),
  });
  if (!res.ok) throw new Error(`WAREHOUSE_GENERATE_ERROR: ${res.status}`);
  return res.json() as Promise<WarehouseSchema>;
}