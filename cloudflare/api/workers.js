export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname === "/") {
      const uid = url.searchParams.get("uid");
      const gid = url.searchParams.get("gid");
      const rid = url.searchParams.get("rid");
      const cond = url.searchParams.get("cond");

      if (!uid || !gid || !rid || !cond) {
        return new Response("不正なリクエストパラメータです。Discordから生成されたリンクを踏んでください。", { status: 400 });
      }

      const state = btoa(JSON.stringify({ uid, gid, rid, cond }));
      
      const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?` +
        `client_id=480825042598-3a9g4uoeoe1orfvcec0utf5hkrv2p634.apps.googleusercontent.com` +
        `&redirect_uri=https://gogleauthbot.system322940-dev.workers.dev/callback` + // 💡ここを変更
        `&response_type=code` +
        `&scope=openid%20profile%20email` +
        `&state=${state}`;

      return Response.redirect(googleAuthUrl, 302);
    }

    if (url.pathname === "/callback") {
      const code = url.searchParams.get("code");
      const stateStr = url.searchParams.get("state");

      if (!code || !stateStr) {
        return new Response("認証コードまたは状態が確認できませんでした。", { status: 400 });
      }

      const { uid, gid, rid, cond } = JSON.parse(atob(stateStr));

      const tokenResponse = await fetch("https://oauth2.googleapis.com/token", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({
          code,
          client_id: "480825042598-3a9g4uoeoe1orfvcec0utf5hkrv2p634.apps.googleusercontent.com",
          client_secret: env.GOOGLE_CLIENT_SECRET, 
          redirect_uri: "https://gogleauthbot.system322940-dev.workers.dev/callback", // 💡ここを変更
          grant_type: "authorization_code"
        })
      });

      const tokenData = await tokenResponse.json();
      if (!tokenData.access_token) {
        return new Response("Googleのトークン取得に失敗しました。", { status: 500 });
      }

      const userResponse = await fetch("https://www.googleapis.com/oauth2/v3/userinfo", {
        headers: { Authorization: `Bearer ${tokenData.access_token}` }
      });
      const userData = await userResponse.json();
      let isEligible = true;
      if (cond === "age_18") {
        isEligible = true; 
      }

      if (!isEligible) {
        return new Response("認証条件を満たしていません。", { status: 403 });
      }

      const discordResponse = await fetch(`https://discord.com/api/v10/guilds/${gid}/members/${uid}/roles/${rid}`, {
        method: "PUT",
        headers: {
          Authorization: `Bot ${env.DISCORD_TOKEN}`,
          "X-Audit-Log-Reason": "Google Auth Verification Success"
        }
      });

      if (discordResponse.ok || discordResponse.status === 204) {
        return Response.redirect("https://googleauthbot.pages.dev/success.html", 302);
      } else {
        const errText = await discordResponse.text();
        return new Response(`Discordのロール付与に失敗しました。Botの権限を確認してください。: ${errText}`, { status: 500 });
      }
    }

    return new Response("Not Found", { status: 404 });
  }
};
