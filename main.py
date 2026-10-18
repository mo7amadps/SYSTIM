import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

# يجب تحميل Secrets قبل استيراد Storage لأن مسار التخزين يُقرأ وقت الاستيراد.
load_dotenv()

from utils.checks import (
    SilentPermissionCheck,
    app_command_setup_preflight,
    prefix_command_permission_check,
)
from utils.storage import Storage

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.members = True          # ضروري لأوامر الرتب والباند والتايم
intents.message_content = True  # ضروري حتى تشتغل تايم / باند / رتب / ان / سجن ...
intents.presences = True        # ضروري لـ !obc وزر "إرسال للأونلاين" (حالة الأعضاء)
if hasattr(intents, "moderation"):
    intents.moderation = True   # ضروري حتى تشتغل مراقبة سجل الأحداث (Audit Log) لنظام الحماية

# ما في بادئة إجبارية لمعظم الأوامر (تايم، باند، …)
# أوامر التذاكر تشتغل كمان بـ !close و !rename


class GuardedCommandTree(app_commands.CommandTree):
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await app_command_setup_preflight(interaction)


bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("+", "!", ""),
    intents=intents,
    help_command=None,
    tree_cls=GuardedCommandTree,
)
bot.add_check(prefix_command_permission_check)

# --- إصلاح خطأ "Unknown message" (كود 50035) ---
# لما رسالة الأمر الأصلية تنشال (تنحذف) قبل ما البوت يرد عليها (مثلاً بوت حماية/سلو مود/أنتي سبام
# تاني شالها، أو المستخدم حذفها بنفسه)، ctx.reply() بيفشل لأنه بيحاول يعمل "رد" على رسالة ما عادت موجودة.
# هلق منلف ctx.reply بحيث لو صار هاد الخطأ بالذات، منرجع نبعت رسالة عادية (ctx.send) بدل ما نكسر الأمر بالكامل.
_original_context_reply = commands.Context.reply


async def _safe_context_reply(self: commands.Context, *args, **kwargs):
    try:
        return await _original_context_reply(self, *args, **kwargs)
    except discord.HTTPException as e:
        if getattr(e, "code", None) == 50035:
            kwargs.pop("mention_author", None)
            kwargs.pop("reference", None)
            return await self.send(*args, **kwargs)
        raise


commands.Context.reply = _safe_context_reply

INITIAL_COGS = [
    "cogs.time_system",
    "cogs.role_system",
    "cogs.ban_system",
    "cogs.security_system",
    "cogs.protection_extra",
    "cogs.rank_system",
    "cogs.reply_system",
    "cogs.moderation_system",
    "cogs.role_assign",
    "cogs.embed_panel",
    "cogs.broadcast_system",
    "cogs.help_system",
    "cogs.unmute_system",
    "cogs.unban_system",
    "cogs.channel_utils",
    "cogs.prison_system",
    "cogs.role_all_system",
    "cogs.tiered_staff_system",
    "cogs.dismiss_system",
    "cogs.xp_system",
    "cogs.quest_system",
    "cogs.dashboard_system",
    "cogs.mention_tracker",
    "cogs.logs_system",
    "cogs.auto_voice_system",
    "cogs.backup_system",
    "cogs.suggestion_system",
    "cogs.auto_role_system",
    "cogs.ticket_system",
    "cogs.giveaway_system",
    "cogs.wheel_system",
    "cogs.filter_system",
    "cogs.games_system",
    "cogs.come_system",
]


async def _sync_slash_commands():
    """مزامنة فورية لكل سيرفر + مزامنة عالمية."""
    for guild in list(bot.guilds):
        try:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            print(f"🔄 مزامنة سيرفر {guild.name}: {len(synced)} أمر")
        except Exception as e:
            print(f"⚠️ فشل sync لـ {guild.id} ({getattr(guild, 'name', '?')}): {e}")
    try:
        synced = await bot.tree.sync()
        print(f"🌍 مزامنة عالمية: {len(synced)} أمر")
    except Exception as e:
        print(f"⚠️ فشلت المزامنة العالمية: {e}")


@bot.event
async def on_ready():
    print(f"✅ سجل الدخول كـ {bot.user} ({bot.user.id}) | السيرفرات: {len(bot.guilds)}")
    await _sync_slash_commands()
    if not periodic_backup_task.is_running():
        periodic_backup_task.start()


@bot.event
async def on_guild_join(guild: discord.Guild):
    try:
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)
        print(f"🔄 مزامنة سيرفر جديد {guild.name}: {len(synced)} أمر")
    except Exception as e:
        print(f"⚠️ فشل sync عند الانضمام لـ {guild.id}: {e}")


@tasks.loop(minutes=15)
async def periodic_backup_task():
    """
    نسخة احتياطية دورية لكل إعدادات البوت - حماية إضافية فوق Transaction
    الموجود أصلاً بقاعدة SQLite في utils/storage.py. لو القاعدة انعطبت أو انمسحت لأي سبب
    (تعطل مفاجئ، مشكلة قرص، إلخ)، البوت بيسترجع تلقائياً من آخر نسخة سليمة
    أول ما يحاول يقرأ الإعدادات - بدون أي تدخل يدوي.
    """
    try:
        await Storage.backup_now()
    except Exception as e:
        print(f"⚠️ فشلت النسخة الاحتياطية الدورية: {e}")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.reply("❌ ما لقيت هاد الشخص، تأكد من المنشن.")
    elif isinstance(error, SilentPermissionCheck):
        # The command intentionally stays completely silent for unauthorized users.
        pass
    elif isinstance(
        error,
        (
            commands.MissingPermissions,
            commands.MissingRole,
            commands.NotOwner,
        ),
    ):
        # كل أوامر النص تبقى صامتة إذا لم تكن لدى المستخدم صلاحيتها.
        pass
    elif isinstance(error, commands.CommandNotFound):
        pass  # نتجاهل أي أمر غير موجود
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"⏳ استنى {error.retry_after:.0f} ثانية قبل ما تعيد الأمر.")
    elif isinstance(error, commands.BadArgument):
        await ctx.reply("❌ تأكد من كتابة الأمر صح.")
    else:
        # قبل كده أي خطأ غير متوقع (زي HTTPException أو أي Exception ثاني) كان بس
        # يتطبع بالـ console وما كان يوصل أي رد للمستخدم، فكان يبين إنه الأمر "ما اشتغل"
        # من غير ما يبين ليش. هلق منرد رسالة واضحة بالإضافة للطباعة بالـ console.
        original = getattr(error, "original", error)
        print(f"خطأ غير متوقع بأمر {ctx.command}: {original!r}")
        try:
            await ctx.reply("❌ صار خطأ غير متوقع وأنا عم أنفذ الأمر. جرب مرة ثانية، ولو تكرر بلغ الأدمن.")
        except discord.HTTPException:
            pass


@bot.tree.error
async def on_app_command_error(
    interaction: discord.Interaction, error: app_commands.AppCommandError
):
    """معالج موحد لأخطاء السلاش بدون رسائل للمستخدم غير المصرح له."""
    if isinstance(
        error,
        (
            app_commands.MissingPermissions,
            app_commands.MissingRole,
            app_commands.CheckFailure,
        ),
    ):
        return

    original = getattr(error, "original", error)
    print(f"خطأ غير متوقع بأمر السلاش: {original!r}")
    if interaction.response.is_done():
        return
    try:
        await interaction.response.send_message(
            "❌ صار خطأ غير متوقع. جرب مرة ثانية.",
            ephemeral=True,
        )
    except discord.HTTPException:
        pass


async def _start_web_dashboard():
    """تشغيل داشبورد الويب جنب البوت (Railway يستخدم PORT)."""
    try:
        import sys
        from pathlib import Path as _P
        root = str(_P(__file__).resolve().parent)
        if root not in sys.path:
            sys.path.insert(0, root)
        import uvicorn
        import webapp
        from utils.storage import Storage as _Storage

        webapp.bot_ref = bot
        webapp.storage_ref = _Storage
        port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
        config = uvicorn.Config(
            webapp.app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            lifespan="on",
        )
        server = uvicorn.Server(config)
        print(f"🌐 Web Dashboard على المنفذ {port}")
        await server.serve()
    except Exception as e:
        import traceback
        print(f"⚠️ فشل تشغيل الداشبورد الويب: {e}")
        traceback.print_exc()


async def main():
    async with bot:
        await Storage.initialize()
        for cog in INITIAL_COGS:
            await bot.load_extension(cog)
        # تشغيل الويب بالتوازي مع البوت
        asyncio.create_task(_start_web_dashboard())
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
