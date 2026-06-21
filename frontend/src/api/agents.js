export async function runFinanceAgent(query) {
  const res = await fetch("/api/agent/finance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });
  if (!res.ok) throw new Error(`Server error ${res.status}`);
  return res.json(); // { price, news, analysis, query }
}
