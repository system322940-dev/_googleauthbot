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
    def __init__(self, age_limit: int):
        super().__init__(timeout=None)
        self.selected_role = None
        self.selected_condition = None
        self.age_limit = age_limit

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="1. 付与するロールを選択してください", min_values=1, max_values=1)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        self.selected_role = select.values[0]
        await interaction.response.defer()

    @discord.ui.select(
        placeholder="2. 認証条件（有効化するもの）を選択してください",
        options=[
            discord.SelectOption(label="Googleアカウント連携のみ", value="google"),
            discord.SelectOption(label="Google連携 + 指定年齢以上(誕生日認証)", value="age_check")
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
            description=f"下のボタンを押してGoogleアカウントと連携し、認証を完了してください。\n"
                        f"※年齢制限が有効な場合、{self.age_limit}歳以上である必要があります。",
            color=discord.Color.blue()
        )
        
        embed.set_footer(text=f"⚙️ System Data: {self.selected_role.id}|{self.selected_condition}|{self.age_limit}")
        
        view = UserVerifyView()
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("認証パネルを設置しました！永続化されているため、Bot再起動後も動作します。", ephemeral=True)


class UserVerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="認証を開始する", style=discord.ButtonStyle.blurple, custom_id="persistent_verify_btn")
    async def start_verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            footer_text = interaction.message.embeds[0].footer.text
            data_str = footer_text.split("System Data: ")[1]
            role_id, condition, age_limit = data_str.split("|")
        except Exception:
            await interaction.response.send_message("パネルデータの読み取りに失敗しました。管理者に連絡して新しくパネルを設置し直してください。", ephemeral=True)
            return

        base_url = "https://googleauthbot.system322940-dev.workers.dev/"
        params = f"?uid={interaction.user.id}&gid={interaction.guild.id}&rid={role_id}&cond={condition}&limit={age_limit}"
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
    bot.add_view(UserVerifyView()) 
    await bot.tree.sync()
    asyncio.create_task(start_server())

@bot.tree.command(name="verify", description="管理用：認証設定パネルを呼び出します。")
@app_commands.describe(age_limit="制限したい年齢を入力（例: 18）※年齢制限を使わない場合も適当に数値を入れてください")
@app_commands.default_permissions(administrator=True)
async def verify_command(interaction: discord.Interaction, age_limit: int = 18):
    view = VerificationSetupView(age_limit)
    await interaction.response.send_message(f"認証の設定を行ってください（設定年齢: {age_limit}歳以上）：", view=view, ephemeral=True)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
