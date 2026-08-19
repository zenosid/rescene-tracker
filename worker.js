// RESCENE Tracker - 익명 반응 카운터 (Cloudflare Worker)
// KV 네임스페이스 바인딩 이름은 "COUNTS"로 설정했다는 전제입니다.

const ALLOWED_EMOJIS = ["👍", "🥹", "🔥", "😍"];
// GitHub Pages 주소만 허용 (다른 곳에서 이 API를 함부로 못 쓰게)
const ALLOWED_ORIGIN = "https://zenosid.github.io";

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": ALLOWED_ORIGIN,
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function jsonResponse(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders() },
  });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    // ── 특정 항목의 현재 반응 개수 조회 ──────────────────
    // ── 여러 항목의 반응 개수를 한 번에 조회 (아카이브처럼 카드가 많을 때,
    // 카드 개수만큼 요청을 따로 보내면 느려지니 한 번의 요청으로 묶어서 처리) ──
    if (request.method === "POST" && url.pathname === "/counts-batch") {
      let body;
      try {
        body = await request.json();
      } catch {
        return jsonResponse({ error: "invalid json" }, 400);
      }
      const ids = Array.isArray(body.ids) ? body.ids.slice(0, 200) : []; // 남용 방지로 상한
      const result = {};
      await Promise.all(
        ids.map(async (id) => {
          const counts = {};
          await Promise.all(
            ALLOWED_EMOJIS.map(async (emoji) => {
              const val = await env.COUNTS.get(`reactions:${id}:${emoji}`);
              counts[emoji] = val ? parseInt(val, 10) : 0;
            })
          );
          result[id] = counts;
        })
      );
      return jsonResponse(result);
    }

    if (request.method === "GET" && url.pathname === "/counts") {
      const itemId = url.searchParams.get("id");
      if (!itemId) return jsonResponse({ error: "id required" }, 400);

      const result = {};
      for (const emoji of ALLOWED_EMOJIS) {
        const val = await env.COUNTS.get(`reactions:${itemId}:${emoji}`);
        result[emoji] = val ? parseInt(val, 10) : 0;
      }
      return jsonResponse(result);
    }

    // ── 반응 추가 ─────────────────────────────────────
    if (request.method === "POST" && url.pathname === "/react") {
      let body;
      try {
        body = await request.json();
      } catch {
        return jsonResponse({ error: "invalid json" }, 400);
      }

      const { id, emoji } = body;
      if (!id || !ALLOWED_EMOJIS.includes(emoji)) {
        return jsonResponse({ error: "invalid id or emoji" }, 400);
      }

      // 같은 IP가 같은 항목에 같은 이모지로 하루에 한 번만 반응하도록 제한
      // (완벽한 어뷰징 방지는 아니지만, 무의미한 연타/조작은 어느 정도 막아줌)
      const ip = request.headers.get("CF-Connecting-IP") || "unknown";
      const today = new Date().toISOString().slice(0, 10);
      const rateLimitKey = `ratelimit:${ip}:${id}:${emoji}:${today}`;
      const alreadyReacted = await env.COUNTS.get(rateLimitKey);
      if (alreadyReacted) {
        return jsonResponse({ error: "이미 오늘 반응하셨습니다" }, 429);
      }

      const countKey = `reactions:${id}:${emoji}`;
      const current = await env.COUNTS.get(countKey);
      const next = (current ? parseInt(current, 10) : 0) + 1;
      await env.COUNTS.put(countKey, String(next));
      // 하루 지나면 자동 만료되도록 TTL 설정 (86400초 = 24시간)
      await env.COUNTS.put(rateLimitKey, "1", { expirationTtl: 86400 });

      return jsonResponse({ [emoji]: next });
    }

    return new Response("Not found", { status: 404, headers: corsHeaders() });
  },
};
