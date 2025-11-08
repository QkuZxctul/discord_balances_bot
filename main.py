import disnake
from disnake.ext import commands
import peewee
from dotenv import load_dotenv
from os import getenv

load_dotenv('.env')

BOT_TOKEN = getenv('BOT_TOKEN')
ADMIN_USER_ID = int(getenv('ADMIN_USER_ID'))
CHANNELS = getenv('CHANNELS_ID')
CHANNELS_ID = [int(x) for x in CHANNELS.split(',')] if ',' in CHANNELS else [int(CHANNELS)]

database = peewee.SqliteDatabase("data/database.db")

class User(peewee.Model):
    user_id = peewee.IntegerField(primary_key=True)
    balance = peewee.IntegerField(default=0)
    class Meta:
        table_name = "users"
        database = database

# database.drop_tables([User])
database.create_tables([User])

# Инициализация бота
intents = disnake.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'Бот {bot.user} запущен!')

def get_balance_db(user_id: int) -> int:
    user_data = User.get_or_none(user_id=user_id)
    if not user_data:
        return 0
    return user_data.balance

def add_balance_db(user_id: int, balance: int) -> None:
    user = User.get_or_none(user_id=user_id)
    if user:
        user.balance += balance
        user.save()
        return
    User.create(user_id=user_id, balance=balance)

def set_balance_db(user_id: int, balance: int) -> bool:
    user = User.get_or_none(user_id=user_id)
    if user:
        user.balance -= balance
        user.save()
        return False
    return True

def get_all_balances() -> list:
    """Получить всех пользователей с ненулевым балансом"""
    return User.select().where(User.balance > 0).order_by(User.balance.desc())

# Команда для просмотра баланса
@bot.slash_command(description="Посмотреть баланс")
async def check_balance(inter: disnake.ApplicationCommandInteraction):
    if inter.channel.id not in CHANNELS_ID:
        return
    user_id = int(inter.author.id)
    balance = get_balance_db(user_id)

    embed = disnake.Embed(
        title=f"Баланс {inter.author.display_name}",
        description=f"💰 Ваш баланс: **{balance}** серебра",
        color=0x00ff00
    )
    await inter.response.send_message(embed=embed)

# Команда для добавления баланса
@bot.slash_command(description="Добавить баланс")
async def add_balance(
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User,
        quantity: str
):
    if inter.channel.id not in CHANNELS_ID:
        return
    quantity = int(quantity.replace(' ', ''))
    # Проверяем, имеет ли пользователь права на выполнение команды
    if inter.author.id != ADMIN_USER_ID:
        embed = disnake.Embed(
            title="Ошибка",
            description="❌ У вас нет прав для выполнения этой команды!",
            color=0xff0000
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    if quantity <= 0:
        embed = disnake.Embed(
            title="Ошибка",
            description="❌ Количество должно быть положительным числом!",
            color=0xff0000
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = int(user.id)
    current_balance = get_balance_db(user_id)
    add_balance_db(user_id, quantity)

    embed = disnake.Embed(
        title="Баланс обновлен",
        description=f"✅ {inter.author.mention} добавил {quantity} монет пользователю {user.mention}",
        color=0x00ff00
    )
    embed.add_field(name="Новый баланс", value=f"💰 {current_balance + quantity} серебра")
    await inter.response.send_message(embed=embed)


# Команда для уменьшения баланса
@bot.slash_command(description="Уменьшить баланс")
async def minus_balance(
        inter: disnake.ApplicationCommandInteraction,
        user: disnake.User,
        quantity: str
):
    if inter.channel.id not in CHANNELS_ID:
        return
    quantity = int(quantity.replace(' ', ''))
    # Проверяем, имеет ли пользователь права на выполнение команды
    if inter.author.id != ADMIN_USER_ID:
        embed = disnake.Embed(
            title="Ошибка",
            description="❌ У вас нет прав для выполнения этой команды!",
            color=0xff0000
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    if quantity <= 0:
        embed = disnake.Embed(
            title="Ошибка",
            description="❌ Количество должно быть положительным числом!",
            color=0xff0000
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    user_id = int(user.id)
    current_balance = get_balance_db(user_id)

    if current_balance < quantity:
        embed = disnake.Embed(
            title="Ошибка",
            description=f"❌ Недостаточно средств! У пользователя только {current_balance} монет",
            color=0xff0000
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    if set_balance_db(user_id, quantity):
        embed = disnake.Embed(
            title="Ошибка",
            description=f"❌ Недостаточно средств! У пользователя нет баланса",
            color=0xff0000
        )
        await inter.response.send_message(embed=embed, ephemeral=True)
        return

    embed = disnake.Embed(
        title="Баланс обновлен",
        description=f"🔻 {inter.author.mention} уменьшил баланс пользователя {user.mention} на {quantity} монет",
        color=0xffa500
    )
    embed.add_field(name="Новый баланс", value=f"💰 {current_balance - quantity} монет")
    await inter.response.send_message(embed=embed)


# Команда для просмотра всех балансов
@bot.slash_command(description="Показать балансы всех пользователей")
async def all_balances(inter: disnake.ApplicationCommandInteraction):
    if inter.channel.id not in CHANNELS_ID:
        return
    users_with_balances = get_all_balances()

    if not users_with_balances:
        embed = disnake.Embed(
            title="Балансы пользователей",
            description="📊 На данный момент никто из пользователей не имеет баланса",
            color=0xffff00
        )
        await inter.response.send_message(embed=embed)
        return

    embed = disnake.Embed(
        title="📊 Балансы всех пользователей",
        description="Список пользователей с ненулевым балансом:",
        color=0x0099ff
    )

    # Разбиваем на страницы если пользователей много
    balance_text = ""
    for i, user in enumerate(users_with_balances, 1):
        try:
            discord_user = await bot.fetch_user(user.user_id)
            username = discord_user.display_name
        except:
            username = f"Пользователь {user.user_id}"

        balance_text += f"**{i}. {username}** - {user.balance} серебра\n"

        # Если текст становится слишком длинным, отправляем текущее сообщение и создаем новое
        if len(balance_text) > 900:
            embed.add_field(
                name="Пользователи",
                value=balance_text,
                inline=False
            )
            await inter.response.send_message(embed=embed)
            embed = disnake.Embed(
                title="📊 Балансы всех пользователей (продолжение)",
                color=0x0099ff
            )
            balance_text = ""

    if balance_text:
        embed.add_field(
            name=f"Всего пользователей с балансом: {len(users_with_balances)}",
            value=balance_text,
            inline=False
        )

        # Добавляем общую сумму
        total_balance = sum(user.balance for user in users_with_balances)
        embed.add_field(
            name="Общий баланс",
            value=f"💰 Всего в системе: **{total_balance}** серебра",
            inline=False
        )

    await inter.response.send_message(embed=embed)


# Запуск бота
if __name__ == "__main__":
    bot.run(BOT_TOKEN)