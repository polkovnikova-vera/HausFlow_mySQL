export type HealthResponse = {
  status: string;
  application: string;
  version: string;
};

export async function loadHealth(): Promise<HealthResponse> {
  const response = await fetch("/api/v1/health", {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) {
    throw new Error(`Health endpoint returned ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
