import os
import discord
from discord.ext import commands
from discord import app_commands
from aiohttp import web
import asyncio

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def handle(request):
    return web.Response(text="Bot is alive!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

class VerificationSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.selected_role = None
        self.selected_condition = None

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="1. 付与するロールを選択してください", min_values=1, max_values=1)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.selected_role = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="2. 認証条件（有効化するもの）を選択してください",
        options=[
            discord.SelectOption(label="Googleアカウント連携のみ", value="google"),
            discord.SelectOption(label="Google連携 + 成人限定(18歳以上)", value="age_18"),
            discord.SelectOption(label="Google連携 + アカウント作成1年以上", value="account_age_1")
        ]
    )
    async def select_condition(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.selected_condition = select.values[0]
        await interaction.response.defer()

    @discord.ui.button(label="設定を確定して認証パネルを送信", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.selected_role or not self.selected_condition:
            await interaction.response.send_message("ロールと条件の両方を選択してください。", ephemeral=True)
            return

        embed = discord.Embed(
            title="Googleアカウント認証",
            description="下のボタンを押してGoogleアカウントと連携し、認証を完了してください。",
            color=discord.Color.blue()
        )
        
        view = UserVerifyView(self.selected_role.id, self.selected_condition)
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("認証パネルを設置しました！", ephemeral=True)


class UserVerifyView(discord.ui.View):
    def __init__(self, role_id, condition):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.condition = condition

    @discord.ui.button(label="認証を開始する", style=discord.ButtonStyle.blurple, custom_id="start_verify_btn")
    async def start_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        base_url = "https://gogleauthbot.system322940-dev.workers.dev/"
        params = f"?uid={interaction.user.id}&gid={interaction.guild.id}&rid={self.role_id}&cond={self.condition}"
        auth_url = base_url + params

        link_view = discord.ui.View()
        link_view.add_item(discord.ui.Button(label="Googleでログインして認証", url=auth_url))
        
        await interaction.response.send_message(
            "あなた専用の認証リンクを作成しました。以下のボタンから連携を行ってください。",
            view=link_view,
            ephemeral=True
        )

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    bot.add_view(UserVerifyView(None, None)) 
    await bot.tree.sync()
    asyncio.create_task(start_server())

@bot.tree.command(name="verify", description="管理用：認証設定パネルを呼び出します。")
@app_commands.default_permissions(administrator=True)
async def verify_command(interaction: discord.Interaction):
    view = VerificationSetupView()
    await interaction.response.send_message("認証の設定を行ってください：", view=view, ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
