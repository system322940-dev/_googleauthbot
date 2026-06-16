import discord
from discord import app_commands
from discord.ext import commands

class VerifierBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        await self.tree.sync()

bot = VerifierBot()

class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_role = None
        self.selected_condition = None

    @discord.ui.select(
        placeholder="付与するロールを選択",
        select_type=discord.ComponentType.role
    )
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_role = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="有効化する条件（年齢 / アカウント作成条件）",
        options=[
            discord.SelectOption(label="Googleのアカウント年齢 (13歳以上など)", value="google_age"),
            discord.SelectOption(label="Discordのアカウント作成からの期間", value="discord_age"),
            discord.SelectOption(label="条件なし（連携のみ）", value="none")
        ]
    )
    async def select_condition(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_condition = select.values[0]
        
        if not self.selected_role:
            await interaction.response.send_message("先にロールを選択してください。", ephemeral=True)
            return

        await interaction.response.send_message("設定が完了しました！以下のボタンから認証メッセージを送信します。", ephemeral=True)
        auth_view = AuthStartView(role_id=self.selected_role.id, condition=self.selected_condition)
        await interaction.channel.send(
            content="🛡️ **サーバー参加者認証**\n下のボタンを押して、Googleアカウント連携を行ってください。",
            view=auth_view
        )

class AuthStartView(discord.ui.View):
    def __init__(self, role_id, condition):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.condition = condition

    @discord.ui.button(label="認証を開始する", style=discord.ButtonStyle.green, custom_id="start_auth_btn")
    async def start_auth(self, interaction: discord.Interaction):
        client_id = "480825042598-3a9g4uoeoe1orfvcec0utf5hkrv2p634.apps.googleusercontent.com"
        redirect_uri = "https://googleauthbot.pages.dev/auth/google/"
        state = f"{interaction.user.id}_{interaction.guild.id}_{self.role_id}_{self.condition}"
        
        google_auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            f"client_id={client_id}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope=openid%20profile%20email&"
            f"state={state}"
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Googleと連携する", url=google_auth_url))
        
        await interaction.response.send_message(
            "以下のボタンからGoogleアカウントとの連携を完了させてください。",
            view=view,
            ephemeral=True
        )

@bot.tree.command(name="verify", description="認証システムの設定を開始します")
@app_commands.checks.has_permissions(administrator=True)
async def verify_setup(interaction: discord.Interaction):
    await interaction.response.send_message(
        "認証Botの設定を行います。2つのプルダウンをそれぞれ選択してください。",
        view=SetupView(),
        ephemeral=True
    )

bot.run("YOUR_DISCORD_BOT_TOKEN")
