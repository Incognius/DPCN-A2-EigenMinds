import { useEffect, useState } from "react";

const cache = new Map<string, Promise<unknown>>();

/** Fetch a JSON file from public/data once; every caller shares the same promise. */
export function loadJSON<T>(name: string): Promise<T> {
  if (!cache.has(name)) {
    cache.set(name, fetch(`./data/${name}`).then((r) => {
      if (!r.ok) throw new Error(`${name}: ${r.status}`);
      return r.json();
    }));
  }
  return cache.get(name) as Promise<T>;
}

export function useData<T>(name: string): { data: T | null; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    loadJSON<T>(name).then((d) => alive && setData(d)).catch((e) => alive && setError(String(e)));
    return () => { alive = false; };
  }, [name]);
  return { data, error };
}
