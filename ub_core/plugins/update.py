import asyncio

from git import Repo

from ub_core import BOT, Config, Message, bot
from ub_core.plugins.restart import restart
from ub_core.utils import run_shell_cmd


async def get_commits(repo: Repo) -> str | None:
    try:
        async with asyncio.timeout(10):
            await asyncio.to_thread(repo.git.fetch)
    except TimeoutError:
        return
    commits: str = ""
    limit: int = 0
    for commit in repo.iter_commits("HEAD..origin/main"):
        commits += (
            f"<b>#{commit.count()}</b> "
            f"<a href='{Config.UPSTREAM_REPO}/commit/{commit}'>{commit.message}</a> "
            f"By <i>{commit.author}</i>"
        )
        limit += 1
        if limit >= 15:
            break
    return commits


async def pull_commits(repo: Repo) -> None | bool:
    repo.git.reset("--hard")
    try:
        async with asyncio.timeout(10):
            await asyncio.to_thread(
                repo.git.pull, Config.UPSTREAM_REPO, "--rebase=true"
            )
            return True
    except TimeoutError:
        return


@bot.add_cmd(cmd="update")
async def updater(bot: BOT, message: Message) -> None | Message:
    """
    CMD: UPDATE
    INFO: Pull / Check for updates.
    FLAGS: -pull to pull updates
    USAGE:
        .update | .update -pull
    """
    reply: Message = await message.reply("Checking for Updates....")
    repo: Repo = Config.REPO
    commits: str = await get_commits(repo)
    if commits is None:
        await reply.edit("Timeout... Try again.")
        return
    if not commits:
        await reply.edit(text="Already Up To Date.", del_in=5)
        return
    if "-pull" not in message.flags:
        await reply.edit(
            text=f"<b>Update Available:</b>\n{commits}", disable_web_page_preview=True
        )
        return
    if not (await pull_commits(repo)):  # NOQA
        await reply.edit("Timeout...Try again.")
        return
    await asyncio.gather(
        bot.log_text(
            text=f"#Updater\nPulled:\n{commits}", disable_web_page_preview=True
        ),
        reply.edit("<b>Update Found</b>\n<i>Pulling....</i>"),
        run_shell_cmd(f"pip install -q --no-cache-dir git+{Config.UPDATE_REPO}"),
    )
    await restart(bot, message, reply)
